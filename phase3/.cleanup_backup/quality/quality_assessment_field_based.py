"""
Field-Based Quality Assessment
Quality is determined by the ability to extract required cheque fields.
A cheque image is GOOD quality only if all critical fields can be extracted.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
from typing import Dict, List, Optional
from dataclasses import dataclass

from extraction.field_extractor_advanced import extract_cheque_fields_advanced
from quality.quality_assessment_unified import UnifiedQualityAssessment


@dataclass
class FieldBasedQualityResult:
    """Field-based quality assessment result"""
    quality_score: float
    quality_status: str  # "GOOD", "UNCERTAIN", "POOR"
    component_scores: Dict[str, float]
    issues: List[str]
    user_message: str
    recommendation: str
    extracted_fields: Dict
    extraction_summary: str
    extractable_count: int
    total_fields: int


class FieldBasedQualityAssessment:
    """
    Assess cheque image quality based on field extraction capability.
    Quality is GOOD if all/most critical fields can be extracted.
    """

    # Critical fields that must be extractable
    CRITICAL_FIELDS = ['cheque_number', 'amount', 'payee_name', 'date']
    # Important fields for complete extraction
    IMPORTANT_FIELDS = ['bank_name', 'account_number', 'micr_code']
    # Optional fields
    OPTIONAL_FIELDS = ['signature']

    # Confidence thresholds
    EXTRACTION_THRESHOLD = 0.35  # Minimum confidence to consider field extractable

    def __init__(self):
        """Initialize field-based assessment"""
        self.traditional_assessment = UnifiedQualityAssessment()

    def assess(self, image_array: np.ndarray, context: str = "user_upload") -> FieldBasedQualityResult:
        """
        Assess image quality based on field extraction capability.

        Args:
            image_array: Image in RGB format
            context: Context of assessment

        Returns:
            FieldBasedQualityResult with quality metrics
        """

        # Get traditional quality metrics (as secondary info)
        traditional_result = self.traditional_assessment.assess(
            image_array=image_array,
            context=context
        )

        # Extract fields and assess extractability
        try:
            extracted_fields = extract_cheque_fields_advanced(image_array)
        except Exception as e:
            print(f"Field extraction error: {e}")
            extracted_fields = {}

        # Analyze extraction results
        extraction_analysis = self._analyze_extraction(extracted_fields)

        # Determine quality status based on extraction
        quality_score, quality_status, issues, user_message, recommendation = \
            self._determine_quality_status(extraction_analysis, traditional_result)

        return FieldBasedQualityResult(
            quality_score=quality_score,
            quality_status=quality_status,
            component_scores=traditional_result.component_scores,
            issues=issues,
            user_message=user_message,
            recommendation=recommendation,
            extracted_fields=extracted_fields,
            extraction_summary=extraction_analysis['summary'],
            extractable_count=extraction_analysis['extractable_count'],
            total_fields=extraction_analysis['total_fields']
        )

    def _analyze_extraction(self, extracted_fields: Dict) -> Dict:
        """
        Analyze field extraction results.

        Args:
            extracted_fields: Dictionary of extracted fields

        Returns:
            Dictionary with extraction analysis
        """

        total_fields = len(extracted_fields)
        extractable_fields = []
        non_extractable_fields = []

        critical_extracted = 0
        important_extracted = 0

        # Analyze each field
        for field_name, field_data in extracted_fields.items():
            is_extractable = (field_data.detected and
                            field_data.confidence >= self.EXTRACTION_THRESHOLD)

            if is_extractable:
                extractable_fields.append({
                    'name': field_name,
                    'confidence': field_data.confidence,
                    'value': field_data.value
                })

                if field_name in self.CRITICAL_FIELDS:
                    critical_extracted += 1
                elif field_name in self.IMPORTANT_FIELDS:
                    important_extracted += 1
            else:
                reason = "Low confidence" if field_data.detected else "Not detected"
                non_extractable_fields.append({
                    'name': field_name,
                    'reason': reason,
                    'confidence': field_data.confidence
                })

        # Generate summary
        summary = (f"Extracted {len(extractable_fields)}/{total_fields} fields. "
                  f"Critical fields: {critical_extracted}/4. "
                  f"Important fields: {important_extracted}/3.")

        return {
            'total_fields': total_fields,
            'extractable_count': len(extractable_fields),
            'extractable_fields': extractable_fields,
            'non_extractable_fields': non_extractable_fields,
            'critical_extracted': critical_extracted,
            'important_extracted': important_extracted,
            'summary': summary
        }

    def _determine_quality_status(self, extraction_analysis: Dict, traditional_result) -> tuple:
        """
        Determine quality status based on field extraction.

        Returns:
            Tuple of (quality_score, quality_status, issues, user_message, recommendation)
        """

        critical_extracted = extraction_analysis['critical_extracted']
        important_extracted = extraction_analysis['important_extracted']
        total_critical = len(self.CRITICAL_FIELDS)
        total_important = len(self.IMPORTANT_FIELDS)
        extractable_count = extraction_analysis['extractable_count']
        total_fields = extraction_analysis['total_fields']

        issues = []
        non_extractable = extraction_analysis['non_extractable_fields']

        # Build issues list
        if non_extractable:
            for field in non_extractable:
                issues.append(f"{field['name'].replace('_', ' ').title()}: {field['reason']} (confidence {field['confidence']:.0%})")

        # Determine quality score and status
        if critical_extracted == total_critical and important_extracted >= total_important - 1:
            # GOOD: All critical fields and most important fields extracted
            quality_score = 0.85
            quality_status = "GOOD"
            user_message = (
                f"✓ Image Quality is GOOD!\n\n"
                f"All critical cheque fields can be extracted successfully.\n"
                f"Extracted: {extractable_count}/{total_fields} fields\n"
                f"Critical fields: {critical_extracted}/{total_critical} ✓"
            )
            recommendation = "Proceed with cheque verification"

        elif critical_extracted >= total_critical - 1 and extractable_count >= total_fields - 2:
            # UNCERTAIN: Most critical fields extracted, but some issues
            quality_score = 0.60
            quality_status = "UNCERTAIN"
            missing_critical = [f for f in non_extractable if f['name'] in self.CRITICAL_FIELDS]
            user_message = (
                f"⚠ Image Quality is UNCERTAIN\n\n"
                f"Some cheque fields cannot be extracted clearly.\n"
                f"Extracted: {extractable_count}/{total_fields} fields\n"
                f"Issues:\n"
            )
            for issue in issues[:3]:  # Show top 3 issues
                user_message += f"  • {issue}\n"

            recommendation = "Try re-uploading with better image quality or lighting"

        else:
            # POOR: Many critical fields cannot be extracted
            quality_score = 0.35
            quality_status = "POOR"
            missing_count = total_fields - extractable_count
            missing_critical = sum(1 for f in non_extractable if f['name'] in self.CRITICAL_FIELDS)

            reason = "Cannot extract required cheque fields. " if missing_critical > 0 else ""
            if missing_critical > 0:
                missing_names = [f['name'].replace('_', ' ').title() for f in non_extractable
                               if f['name'] in self.CRITICAL_FIELDS]
                reason += f"Missing critical fields: {', '.join(missing_names[:2])}"

            user_message = (
                f"✗ Image Quality is POOR\n\n"
                f"Cannot extract critical cheque fields from this image.\n"
                f"Reason: {reason}\n\n"
                f"Extracted: {extractable_count}/{total_fields} fields"
            )
            recommendation = "Upload a clear image with proper lighting and all cheque fields visible"

        # Add traditional quality issues if relevant
        if traditional_result.issues:
            for issue in traditional_result.issues[:2]:
                if issue not in issues:
                    issues.insert(0, issue)

        return quality_score, quality_status, issues, user_message, recommendation
