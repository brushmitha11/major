"""
PHASE 3 — IMAGE QUALITY ASSESSMENT API

FastAPI backend for image quality assessment.
Wraps UnifiedQualityAssessment for web consumption.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import io
import cv2
import numpy as np
from quality.quality_assessment_unified import UnifiedQualityAssessment
from quality.quality_assessment_field_based import FieldBasedQualityAssessment
from localization.field_localization import FieldLocalizationV1
from extraction.field_extractor import extract_cheque_fields
from extraction.field_extractor_advanced import extract_cheque_fields_advanced


# Pydantic models for API responses
class ComponentScores(BaseModel):
    sharpness: float
    contrast: float
    brightness: float
    skew: float
    completeness: float


class QualityResponse(BaseModel):
    quality_score: float
    quality_status: str  # "GOOD", "UNCERTAIN", "POOR"
    component_scores: ComponentScores
    issues: List[str]
    user_message: str
    recommendation: str


class HealthResponse(BaseModel):
    status: str
    message: str


class ExtractedChequeField(BaseModel):
    field_name: str
    detected: bool
    confidence: float
    value: Optional[str] = None


class FieldExtractionResult(BaseModel):
    field_name: str
    extracted: bool
    confidence: float
    location: Optional[Dict] = None


class EnhancedQualityResponse(BaseModel):
    quality_score: float
    quality_percentage: float
    quality_status: str
    component_scores: ComponentScores
    issues: List[str]
    user_message: str
    recommendation: str
    fields_extractable: bool
    extracted_fields: List[FieldExtractionResult]
    field_extraction_message: str
    cheque_fields: List[ExtractedChequeField]


# Initialize FastAPI app
app = FastAPI(
    title="Cheque Image Quality Assessment API",
    description="Assess image quality for cheque processing",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (adjust for production)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize assessment engines
quality_engine = UnifiedQualityAssessment()
field_based_quality_engine = FieldBasedQualityAssessment()
try:
    field_localization = FieldLocalizationV1()
except Exception as e:
    print(f"Warning: Field localization not available: {e}")
    field_localization = None


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "message": "Image quality assessment API is running"
    }


@app.post("/assess", response_model=QualityResponse)
async def assess_image(file: UploadFile = File(...)):
    """
    Assess image quality from uploaded file.

    Args:
        file: Image file (JPEG, PNG, TIFF, etc.)

    Returns:
        QualityResponse with quality metrics and user-friendly messages
    """
    try:
        # Read file content
        contents = await file.read()

        # Validate file
        if not contents:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Convert bytes to numpy array
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(
                status_code=400,
                detail="Could not decode image. Ensure it is a valid image file (JPEG, PNG, TIFF, etc.)"
            )

        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Assess quality
        quality_result = quality_engine.assess(
            image_array=image,
            context="user_upload"
        )

        # Build response
        return QualityResponse(
            quality_score=round(quality_result.quality_score, 3),
            quality_status=quality_result.quality_status,
            component_scores=ComponentScores(
                sharpness=round(quality_result.component_scores["sharpness"], 3),
                contrast=round(quality_result.component_scores["contrast"], 3),
                brightness=round(quality_result.component_scores["brightness"], 3),
                skew=round(quality_result.component_scores["skew"], 3),
                completeness=round(quality_result.component_scores["completeness"], 3),
            ),
            issues=quality_result.issues,
            user_message=quality_result.user_message,
            recommendation=quality_result.recommendation,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error assessing image quality: {str(e)}"
        )


@app.post("/assess-comprehensive", response_model=EnhancedQualityResponse)
async def assess_comprehensive(file: UploadFile = File(...), bank: str = "GENERIC"):
    """
    Comprehensive cheque assessment including quality and field extraction.

    Args:
        file: Image file (JPEG, PNG, TIFF, etc.)
        bank: Bank code for field localization template

    Returns:
        EnhancedQualityResponse with quality metrics and field extraction results
    """
    try:
        # Read file content
        contents = await file.read()

        if not contents:
            raise HTTPException(status_code=400, detail="Empty file uploaded")

        # Convert bytes to numpy array
        nparr = np.frombuffer(contents, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise HTTPException(
                status_code=400,
                detail="Could not decode image"
            )

        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Assess quality based on field extraction capability
        quality_result = field_based_quality_engine.assess(
            image_array=image_rgb,
            context="user_upload"
        )

        # Extract cheque-specific fields with text recognition
        cheque_fields = []
        try:
            # Try advanced extraction with OCR first
            try:
                extracted_fields_dict = extract_cheque_fields_advanced(image_rgb)
            except Exception:
                # Fallback to basic extraction
                extracted_fields_dict = extract_cheque_fields(image_rgb)

            cheque_fields = [
                ExtractedChequeField(
                    field_name=field.field_name,
                    detected=field.detected,
                    confidence=round(field.confidence, 3),
                    value=field.value
                )
                for field in extracted_fields_dict.values()
            ]
        except Exception as e:
            print(f"Cheque field extraction error: {e}")

        # Extract localization fields if available
        extracted_fields = []
        fields_extractable = False
        field_extraction_message = "Field extraction not available"

        if field_localization:
            try:
                localization_result = field_localization.localize_fields(
                    image=image_rgb,
                    bank=bank,
                    quality_score=quality_result.quality_score
                )

                fields_extractable = localization_result.status == 'success'

                # Build field results
                for field_name, field_result in localization_result.fields.items():
                    extracted_fields.append(FieldExtractionResult(
                        field_name=field_name,
                        extracted=field_result.is_valid if hasattr(field_result, 'is_valid') else False,
                        confidence=getattr(field_result, 'confidence', 0.0),
                        location=getattr(field_result, 'bounds', None)
                    ))

                if fields_extractable:
                    field_extraction_message = f"Successfully extracted {localization_result.successful_fields}/{localization_result.total_fields} fields"
                else:
                    field_extraction_message = localization_result.failure_reason or "Field extraction failed"

            except Exception as e:
                field_extraction_message = f"Field extraction error: {str(e)}"

        # Build response
        quality_percentage = round(quality_result.quality_score * 100, 1)

        return EnhancedQualityResponse(
            quality_score=round(quality_result.quality_score, 3),
            quality_percentage=quality_percentage,
            quality_status=quality_result.quality_status,
            component_scores=ComponentScores(
                sharpness=round(quality_result.component_scores["sharpness"], 3),
                contrast=round(quality_result.component_scores["contrast"], 3),
                brightness=round(quality_result.component_scores["brightness"], 3),
                skew=round(quality_result.component_scores["skew"], 3),
                completeness=round(quality_result.component_scores["completeness"], 3),
            ),
            issues=quality_result.issues,
            user_message=quality_result.user_message,
            recommendation=quality_result.recommendation,
            fields_extractable=fields_extractable,
            extracted_fields=extracted_fields,
            field_extraction_message=field_extraction_message,
            cheque_fields=cheque_fields,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in comprehensive assessment: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
