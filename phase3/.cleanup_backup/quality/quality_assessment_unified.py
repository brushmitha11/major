"""
Unified Quality Assessment Engine

Wraps the existing ImageQualityAssessment class.
Provides consistent interface for both dataset analysis and user-upload contexts.

PROVISIONAL THRESHOLDS (NOT scientifically validated):
- GOOD: >= 0.65
- UNCERTAIN: 0.50-0.65
- POOR: < 0.50

The existing equal-weight composition (0.2 each) is the approved baseline
and is not yet scientifically validated or optimized.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
from typing import Optional

from preprocessing.image_quality import ImageQualityAssessment
from quality.quality_result import QualityResult


class UnifiedQualityAssessment:
    """
    Unified wrapper around ImageQualityAssessment for both contexts:
    - Dataset analysis (research)
    - User-upload quality gate
    """

    # PROVISIONAL thresholds (configurable)
    GOOD_THRESHOLD = 0.65
    UNCERTAIN_THRESHOLD = 0.50

    # Issue message mapping
    ISSUE_MESSAGES = {
        "low_sharpness": "The image appears blurry.",
        "poor_contrast": "The cheque details may be difficult to read due to low contrast.",
        "poor_brightness": "The image brightness may make cheque details difficult to read.",
        "excessive_skew": "The cheque appears tilted. Please photograph it straight-on.",
        "incomplete_cheque": "The complete cheque may not be visible.",
    }

    def __init__(self, config: Optional[dict] = None):
        """
        Initialize unified quality assessment.

        Args:
            config: Optional configuration dict with:
                - good_threshold: float (default 0.65)
                - uncertain_threshold: float (default 0.50)
        """
        self.engine = ImageQualityAssessment()

        if config:
            self.GOOD_THRESHOLD = config.get("good_threshold", self.GOOD_THRESHOLD)
            self.UNCERTAIN_THRESHOLD = config.get("uncertain_threshold", self.UNCERTAIN_THRESHOLD)

    def assess(self, image_path: Optional[str] = None, image_array: Optional[np.ndarray] = None,
               context: str = "dataset") -> QualityResult:
        """
        Assess image quality.

        Args:
            image_path: Path to image file
            image_array: Numpy array (if image_path not provided)
            context: "dataset" or "user_upload"

        Returns:
            QualityResult with all metrics and user-facing messages
        """
        # Load image
        if image_path:
            image = cv2.imread(str(image_path))
            if image is None:
                raise FileNotFoundError(f"Cannot load image: {image_path}")
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        elif image_array is not None:
            image = image_array
        else:
            raise ValueError("Either image_path or image_array must be provided")

        # Get component scores from existing engine
        quality_dict = self.engine.assess_image_quality(image)

        # Extract component scores
        component_scores = {
            "sharpness": quality_dict["sharpness"],
            "contrast": quality_dict["contrast"],
            "brightness": quality_dict["brightness"],
            "skew": quality_dict["skew"],
            "completeness": quality_dict["completeness"],
        }

        # Reuse the existing combined score calculation
        combined_score = quality_dict["combined_score"]

        # Determine quality status
        if combined_score >= self.GOOD_THRESHOLD:
            quality_status = "GOOD"
        elif combined_score >= self.UNCERTAIN_THRESHOLD:
            quality_status = "UNCERTAIN"
        else:
            quality_status = "POOR"

        # Detect issues
        issues = self._detect_issues(component_scores)

        # Create result
        result = QualityResult(
            quality_score=combined_score,
            quality_status=quality_status,
            component_scores=component_scores,
            issues=issues,
            image_path=image_path,
            context=context,
            threshold_good=self.GOOD_THRESHOLD,
            threshold_uncertain=self.UNCERTAIN_THRESHOLD,
        )

        return result

    def _detect_issues(self, component_scores: dict) -> list:
        """Detect and report quality issues based on component scores."""
        issues = []

        # Sharpness threshold (0.5 is low)
        if component_scores["sharpness"] < 0.5:
            issues.append(self.ISSUE_MESSAGES["low_sharpness"])

        # Contrast threshold (0.3 is poor)
        if component_scores["contrast"] < 0.3:
            issues.append(self.ISSUE_MESSAGES["poor_contrast"])

        # Brightness threshold (0.4 is problematic)
        if component_scores["brightness"] < 0.4:
            issues.append(self.ISSUE_MESSAGES["poor_brightness"])

        # Skew threshold (< 0.7 indicates excessive rotation)
        if component_scores["skew"] < 0.7:
            issues.append(self.ISSUE_MESSAGES["excessive_skew"])

        # Completeness threshold (< 0.7 means incomplete)
        if component_scores["completeness"] < 0.7:
            issues.append(self.ISSUE_MESSAGES["incomplete_cheque"])

        return issues


# Convenience function
def assess_image_quality(image_path: Optional[str] = None,
                         image_array: Optional[np.ndarray] = None,
                         context: str = "dataset") -> QualityResult:
    """Convenience function to assess image quality."""
    engine = UnifiedQualityAssessment()
    return engine.assess(image_path=image_path, image_array=image_array, context=context)
