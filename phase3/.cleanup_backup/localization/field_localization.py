"""
Phase 3 Field Localization V1 — High-Level Orchestrator

Template-based field localization pipeline:
1. Bank validation and template selection
2. Cheque corner detection and registration
3. Field extraction and cropping
4. Result aggregation

PROVISIONAL PARAMETERS:
All template field bounding boxes are PLACEHOLDER ESTIMATES, not ground-truth annotations.
Coordinates must be independently refined/validated for each bank.

Data Protection: No CSV files loaded. Templates developed under TRAIN-only methodology.
TEST data completely protected until final evaluation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np
import logging

from .templates import get_template, TEMPLATE_REGISTRY
from .registration import (
    detect_cheque_corners,
    compute_affine_transform,
    compute_confidence_from_residual,
    validate_affine_transform
)
from .crops import extract_field_crop, CropResult

logger = logging.getLogger(__name__)


@dataclass
class FieldLocalizationResult:
    """Complete localization result for one cheque image"""

    # Input metadata
    bank: str
    image_shape: Tuple[int, int, int]  # (H, W, C)
    quality_score: Optional[float] = None  # Informational/diagnostic only

    # Registration status
    registration_success: bool = False
    registration_confidence: float = 0.0  # Diagnostic measure only [0.0, 1.0]
    registration_residual: Optional[float] = None  # RMSE in pixels

    # Detected/registered corners
    detected_corners: Optional[List[Tuple[int, int]]] = None  # [TL, TR, BR, BL]
    affine_matrix: Optional[np.ndarray] = None  # 2x3 transformation matrix

    # Transformation diagnostics (provisional/diagnostic only)
    transform_params: Optional[Dict] = None  # {sx, sy, rotation_deg, translation}

    # Per-field results
    fields: Dict[str, CropResult] = field(default_factory=dict)

    # Overall status
    status: str = 'complete_failure'  # 'success' | 'partial_failure' | 'complete_failure'
    applicable_fields: List[str] = field(default_factory=list)  # Fields for this bank
    successful_fields: int = 0  # Count of valid crops
    total_fields: int = 0  # Total applicable fields

    # Failure information
    failure_reason: Optional[str] = None

    # Metadata
    timestamp: datetime = field(default_factory=datetime.now)
    debug_info: Dict = field(default_factory=dict)


class FieldLocalizationV1:
    """
    V1 Template-Based Field Localization

    Extracts cheque field regions (amount, payee, date, signature) using bank-specific
    templates and affine image registration.

    PURPOSE: Extract field crops for downstream verification processing.
    NOT a forgery detector.

    TEMPLATES: PROVISIONAL PLACEHOLDER ESTIMATES only.
    CONFIDENCE: Registration quality diagnostic measure only.
    """

    def __init__(self):
        """Initialize localization module"""
        self.template_registry = TEMPLATE_REGISTRY
        logger.info("FieldLocalizationV1 initialized")

    def localize_fields(
        self,
        image: np.ndarray,
        bank: str,
        quality_score: Optional[float] = None
    ) -> FieldLocalizationResult:
        """
        Extract field regions from a cheque image using bank-specific template.

        Pipeline:
        1. Validate bank and obtain template
        2. Detect cheque corners (registration.py)
        3. Compute affine transformation
        4. Extract applicable fields (crops.py)
        5. Aggregate results

        Args:
            image: RGB uint8 cheque image
            bank: 'AXIS BANK' | 'CANARA BANK' | 'ICICI BANK' | 'SYNDICATE BANK'
            quality_score: Optional quality assessment score (informational/diagnostic only)

        Returns:
            FieldLocalizationResult with complete localization output
        """
        # Initialize result
        result = FieldLocalizationResult(
            bank=bank,
            image_shape=image.shape,
            quality_score=quality_score
        )

        # Step 1: Validate bank and get template
        template = self._validate_bank_and_get_template(bank)
        if template is None:
            result.status = 'complete_failure'
            result.failure_reason = f"Unknown or unsupported bank: {bank}"
            logger.error(f"Unknown bank: {bank}")
            return result

        # Get applicable fields for this bank
        applicable_fields = template.get_applicable_fields()
        result.applicable_fields = [f.name for f in applicable_fields]
        result.total_fields = len(applicable_fields)

        logger.info(f"Processing {bank}: {len(applicable_fields)} applicable fields")

        # Step 2: Detect corners and register
        detected_corners = detect_cheque_corners(image)

        if detected_corners is None or len(detected_corners) < 3:
            # Registration failed - create invalid CropResults for all fields
            logger.warning("Corner detection failed")
            result.registration_success = False
            result.registration_confidence = 0.0
            result.status = 'complete_failure'
            result.failure_reason = "Registration failed: insufficient or invalid corners detected"

            # Create CropResult for each field with failure reason
            for field_def in applicable_fields:
                result.fields[field_def.name] = CropResult(
                    field=field_def.name,
                    crop=None,
                    bbox_original=field_def.bbox_canonical,
                    bbox_transformed=None,
                    is_valid=False,
                    reason="No affine transformation (registration failed)"
                )

            return result

        result.detected_corners = detected_corners

        # Get canonical corners from template
        canonical_corners = list(template.canonical_corners)

        # Compute affine transformation
        affine_matrix, residual, diagnostics = compute_affine_transform(
            canonical_corners, detected_corners
        )

        if affine_matrix is None:
            # Affine computation failed - create invalid CropResults
            logger.warning("Affine transformation computation failed")
            result.registration_success = False
            result.registration_confidence = 0.0
            result.status = 'complete_failure'
            result.failure_reason = "Affine transformation failed or matrix is singular"

            for field_def in applicable_fields:
                result.fields[field_def.name] = CropResult(
                    field=field_def.name,
                    crop=None,
                    bbox_original=field_def.bbox_canonical,
                    bbox_transformed=None,
                    is_valid=False,
                    reason="No affine transformation (registration failed)"
                )

            return result

        # Validate affine matrix
        is_valid, validation_reason = validate_affine_transform(affine_matrix)
        if not is_valid:
            logger.warning(f"Affine matrix validation failed: {validation_reason}")
            result.registration_success = False
            result.registration_confidence = 0.0
            result.status = 'complete_failure'
            result.failure_reason = f"Affine matrix validation failed: {validation_reason}"

            for field_def in applicable_fields:
                result.fields[field_def.name] = CropResult(
                    field=field_def.name,
                    crop=None,
                    bbox_original=field_def.bbox_canonical,
                    bbox_transformed=None,
                    is_valid=False,
                    reason="No affine transformation (registration failed)"
                )

            return result

        # Registration succeeded
        result.registration_success = True
        result.affine_matrix = affine_matrix
        result.registration_residual = residual
        result.transform_params = diagnostics

        # Compute registration confidence (diagnostic measure only)
        scale_factors = (diagnostics.get('sx', 1.0), diagnostics.get('sy', 1.0))
        rotation = diagnostics.get('rotation_deg', 0.0)
        confidence = compute_confidence_from_residual(
            residual=residual,
            rotation_deg=rotation,
            scale_factors=scale_factors,
            tolerance_pixels=10.0  # PROVISIONAL diagnostic tolerance
        )
        result.registration_confidence = confidence

        logger.info(
            f"Registration succeeded: residual={residual:.2f}px, "
            f"confidence={confidence:.3f}, rotation={rotation:.1f}°"
        )

        # Step 3: Extract field crops
        for field_def in applicable_fields:
            crop_result = extract_field_crop(
                image=image,
                field_name=field_def.name,
                bbox_canonical=field_def.bbox_canonical,
                affine_matrix=affine_matrix,
                target_size=(256, 128)  # Standard crop size
            )
            result.fields[field_def.name] = crop_result

            if crop_result.is_valid:
                result.successful_fields += 1
                logger.info(f"  {field_def.name}: extracted successfully")
            else:
                logger.warning(f"  {field_def.name}: {crop_result.reason}")

        # Step 4: Determine overall status
        if result.successful_fields == result.total_fields:
            result.status = 'success'
        elif result.successful_fields > 0:
            result.status = 'partial_failure'
            result.failure_reason = (
                f"Partial localization: {result.successful_fields}/{result.total_fields} fields extracted"
            )
        else:
            result.status = 'complete_failure'
            result.failure_reason = "No fields successfully extracted"

        # Add debug info
        result.debug_info = {
            'corner_detection_method': 'Canny + Contours + Quadrilateral Approximation',
            'registration_method': 'cv2.getAffineTransform (3 pts) or cv2.estimateAffine2D (4+ pts)',
            'crop_size': (256, 128),
            'template_status': 'placeholder_estimate',
            'template_note': 'All coordinates are PROVISIONAL estimates, not ground-truth annotations'
        }

        return result

    def _validate_bank_and_get_template(self, bank: str):
        """
        Validate bank name and return corresponding template.

        Args:
            bank: Bank name string

        Returns:
            Template object or None if bank is unknown
        """
        if bank not in self.template_registry:
            logger.warning(f"Unknown bank: {bank}")
            return None

        template = get_template(bank)
        if template is None:
            logger.warning(f"Failed to load template for bank: {bank}")
            return None

        return template
