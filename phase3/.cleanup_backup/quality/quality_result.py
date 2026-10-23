"""
Quality Assessment Result — Common structure for dataset and user contexts.

PROVISIONAL THRESHOLDS (NOT scientifically validated):
- GOOD: quality_score >= 0.65
- UNCERTAIN: 0.50 <= quality_score < 0.65
- POOR: quality_score < 0.50
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class QualityResult:
    """Unified quality assessment result for both dataset analysis and user uploads."""

    # Overall quality metrics
    quality_score: float                    # [0.0, 1.0] composite score
    quality_status: str                     # "GOOD", "UNCERTAIN", or "POOR"

    # Component scores (0.0-1.0 range)
    component_scores: Dict[str, float] = field(default_factory=dict)
    # Keys: "sharpness", "contrast", "brightness", "skew", "completeness"

    # Issues detected (user-friendly descriptions)
    issues: List[str] = field(default_factory=list)

    # User-facing messages
    user_message: str = ""                  # Human-friendly quality summary
    recommendation: str = ""                # "Continue" / "Re-upload"

    # Metadata
    image_path: Optional[str] = None
    context: str = "dataset"                # "dataset" or "user_upload"

    # Threshold used (for diagnostics)
    threshold_good: float = 0.65            # PROVISIONAL
    threshold_uncertain: float = 0.50       # PROVISIONAL

    def __post_init__(self):
        """Validate and generate user-facing messages if not provided."""
        if not self.user_message:
            self._generate_user_message()

        if not self.recommendation:
            self._generate_recommendation()

    def _generate_user_message(self) -> None:
        """Generate user-friendly message based on quality status."""
        if self.quality_status == "GOOD":
            self.user_message = (
                "Image Quality: Good [OK]\n\n"
                "The cheque image is clear enough for automated verification.\n\n"
                "Proceeding with verification..."
            )

        elif self.quality_status == "UNCERTAIN":
            self.user_message = (
                "Image Quality: Uncertain [WARN]\n\n"
                "The image quality may affect verification reliability.\n\n"
                "Please re-upload a clearer image before continuing."
            )

        elif self.quality_status == "POOR":
            issues_str = "\n".join(f"- {issue}" for issue in self.issues)
            self.user_message = (
                "Image Quality: Poor [WARN]\n\n"
                "We cannot reliably process this cheque image.\n\n"
                "Problems detected:\n"
                f"{issues_str}\n\n"
                "Please re-upload a clear, complete image of the cheque."
            )

    def _generate_recommendation(self) -> None:
        """Generate recommendation based on quality status."""
        if self.quality_status == "GOOD":
            self.recommendation = "Continue to verification"
        else:
            self.recommendation = "Re-upload image"

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        return {
            "quality_score": round(self.quality_score, 3),
            "quality_status": self.quality_status,
            "sharpness": round(self.component_scores.get("sharpness", 0), 3),
            "contrast": round(self.component_scores.get("contrast", 0), 3),
            "brightness": round(self.component_scores.get("brightness", 0), 3),
            "skew": round(self.component_scores.get("skew", 0), 3),
            "completeness": round(self.component_scores.get("completeness", 0), 3),
            "issues": "; ".join(self.issues) if self.issues else "None",
            "context": self.context,
        }
