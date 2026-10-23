"""
Cheque Field Extraction Module
Extracts specific fields from cheque images using template-based approach
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass


@dataclass
class ExtractedField:
    """Result of field extraction"""
    field_name: str
    detected: bool
    confidence: float
    value: Optional[str] = None
    region: Optional[np.ndarray] = None


class ChequeFieldExtractor:
    """
    Extract predefined fields from cheque images.
    Uses template-based localization to identify field regions.
    """

    # Standard cheque field regions (normalized coordinates 0-1)
    # Adjusted for better detection across various cheque formats
    FIELD_REGIONS = {
        'cheque_number': {'region': (0.65, 0.03, 0.98, 0.12), 'field_type': 'numeric'},
        'bank_name': {'region': (0.02, 0.05, 0.5, 0.15), 'field_type': 'text'},
        'account_number': {'region': (0.02, 0.30, 0.5, 0.42), 'field_type': 'numeric'},
        'date': {'region': (0.65, 0.15, 0.98, 0.25), 'field_type': 'date'},
        'payee_name': {'region': (0.02, 0.17, 0.95, 0.28), 'field_type': 'text'},
        'amount': {'region': (0.65, 0.26, 0.98, 0.36), 'field_type': 'numeric'},
        'signature': {'region': (0.60, 0.70, 0.98, 0.95), 'field_type': 'signature'},
        'micr_code': {'region': (0.02, 0.92, 0.98, 0.99), 'field_type': 'numeric'},
    }

    def __init__(self):
        """Initialize field extractor"""
        self.fields = self.FIELD_REGIONS

    def extract_fields(self, image: np.ndarray) -> Dict[str, ExtractedField]:
        """
        Extract all defined fields from image.

        Args:
            image: Input image (RGB, numpy array)

        Returns:
            Dictionary of ExtractedField objects
        """
        results = {}
        height, width = image.shape[:2]

        for field_name, field_info in self.fields.items():
            # Get normalized region
            x_min, y_min, x_max, y_max = field_info['region']

            # Convert to pixel coordinates
            px_min = int(x_min * width)
            py_min = int(y_min * height)
            px_max = int(x_max * width)
            py_max = int(y_max * height)

            # Ensure bounds are valid
            px_min = max(0, min(px_min, width - 1))
            px_max = max(px_min + 1, min(px_max, width))
            py_min = max(0, min(py_min, height - 1))
            py_max = max(py_min + 1, min(py_max, height))

            # Extract region
            region = image[py_min:py_max, px_min:px_max]

            # Check if region is valid and has content
            if region.size > 0:
                # Calculate confidence based on region properties
                confidence = self._calculate_region_confidence(region, field_info['field_type'])
                detected = confidence > 0.3

                results[field_name] = ExtractedField(
                    field_name=field_name,
                    detected=detected,
                    confidence=confidence,
                    value=None,
                    region=region
                )
            else:
                results[field_name] = ExtractedField(
                    field_name=field_name,
                    detected=False,
                    confidence=0.0,
                    value=None,
                    region=None
                )

        return results

    def _calculate_region_confidence(self, region: np.ndarray, field_type: str) -> float:
        """
        Calculate confidence score for a region.
        Based on contrast, content, and visibility.

        Args:
            region: Image region
            field_type: Type of field (text, numeric, signature, date)

        Returns:
            Confidence score (0-1)
        """
        if region.size == 0:
            return 0.0

        # Convert to grayscale if needed
        if len(region.shape) == 3:
            gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        else:
            gray = region

        # Calculate metrics
        mean_val = np.mean(gray)
        std_val = np.std(gray)

        # Normalized standard deviation (contrast indicator)
        contrast = std_val / 256.0

        # Check if region has visible content
        # Content is between too dark (0-50) and too bright (200-255)
        has_content = 50 < mean_val < 200

        # Calculate confidence based on contrast and content
        # Base confidence from contrast (std deviation)
        confidence = min(contrast * 3, 1.0)  # Scale up contrast sensitivity

        # Boost confidence if region has content
        if has_content:
            confidence = min(confidence * 1.3, 1.0)

        # Minimum baseline - regions with any variance are considered detected
        confidence = max(confidence, 0.4) if has_content else max(confidence, 0.2)

        return min(confidence, 1.0)

    def get_field_locations(self) -> Dict[str, Dict]:
        """Get information about field locations"""
        return {
            name: {
                'name': name,
                'region': field_info['region'],
                'type': field_info['field_type'],
                'description': f"Cheque {name.replace('_', ' ').title()}"
            }
            for name, field_info in self.fields.items()
        }


def extract_cheque_fields(image: np.ndarray) -> Dict[str, ExtractedField]:
    """
    Convenience function to extract fields from image.

    Args:
        image: Input image (RGB, numpy array)

    Returns:
        Dictionary of extracted fields
    """
    extractor = ChequeFieldExtractor()
    return extractor.extract_fields(image)
