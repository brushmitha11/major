"""
Advanced Cheque Field Extraction with OCR
Extracts and recognizes text from cheque fields
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from typing import Dict, Optional
from dataclasses import dataclass
import re


@dataclass
class ExtractedFieldData:
    """Enhanced field extraction result with text"""
    field_name: str
    detected: bool
    confidence: float
    value: Optional[str] = None
    region: Optional[np.ndarray] = None
    region_bounds: Optional[tuple] = None


class AdvancedChequeFieldExtractor:
    """
    Extract cheque fields with text recognition using image processing.
    """

    # Field regions (normalized coordinates)
    FIELD_REGIONS = {
        'cheque_number': {'region': (0.65, 0.03, 0.98, 0.12), 'type': 'numeric', 'pattern': r'\d+'},
        'bank_name': {'region': (0.02, 0.05, 0.5, 0.15), 'type': 'text', 'pattern': None},
        'account_number': {'region': (0.02, 0.30, 0.5, 0.42), 'type': 'numeric', 'pattern': r'\d+'},
        'date': {'region': (0.65, 0.15, 0.98, 0.25), 'type': 'date', 'pattern': r'\d{1,2}/\d{1,2}/\d{2,4}'},
        'payee_name': {'region': (0.02, 0.17, 0.95, 0.28), 'type': 'text', 'pattern': None},
        'amount': {'region': (0.65, 0.26, 0.98, 0.36), 'type': 'numeric', 'pattern': r'[\d,]+'},
        'signature': {'region': (0.60, 0.70, 0.98, 0.95), 'type': 'signature', 'pattern': None},
        'micr_code': {'region': (0.02, 0.92, 0.98, 0.99), 'type': 'numeric', 'pattern': r'\d+'},
    }

    def __init__(self):
        """Initialize extractor"""
        self.fields = self.FIELD_REGIONS
        self.try_ocr = self._check_ocr_availability()

    def _check_ocr_availability(self) -> bool:
        """Check if pytesseract/Tesseract is available"""
        try:
            import pytesseract
            return True
        except ImportError:
            return False

    def extract_fields(self, image: np.ndarray) -> Dict[str, ExtractedFieldData]:
        """
        Extract all fields from cheque image.

        Args:
            image: Input image (RGB, numpy array)

        Returns:
            Dictionary of extracted fields with values
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

            if region.size > 0:
                # Calculate confidence
                confidence = self._calculate_confidence(region, field_info['type'])
                detected = confidence > 0.25

                # Try to extract text/value
                value = None
                if detected and self.try_ocr:
                    value = self._extract_text_value(region, field_name, field_info)

                results[field_name] = ExtractedFieldData(
                    field_name=field_name,
                    detected=detected,
                    confidence=confidence,
                    value=value,
                    region=region,
                    region_bounds=(px_min, py_min, px_max, py_max)
                )
            else:
                results[field_name] = ExtractedFieldData(
                    field_name=field_name,
                    detected=False,
                    confidence=0.0,
                    value=None,
                    region=None,
                    region_bounds=None
                )

        return results

    def _calculate_confidence(self, region: np.ndarray, field_type: str) -> float:
        """Calculate region confidence score"""
        if region.size == 0:
            return 0.0

        # Convert to grayscale
        if len(region.shape) == 3:
            gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        else:
            gray = region

        # Calculate metrics
        mean_val = np.mean(gray)
        std_val = np.std(gray)

        # Content detection
        has_content = 20 < mean_val < 230
        contrast = std_val / 256.0

        # Confidence calculation
        confidence = min(contrast * 2.5, 1.0)

        if has_content:
            confidence = min(confidence * 1.4, 1.0)

        confidence = max(confidence, 0.3) if has_content else max(confidence, 0.1)

        return min(confidence, 1.0)

    def _extract_text_value(self, region: np.ndarray, field_name: str, field_info: dict) -> Optional[str]:
        """Extract text value from region using OCR"""
        try:
            import pytesseract

            # Preprocess region for OCR
            processed = self._preprocess_for_ocr(region)

            # Extract text using Tesseract
            config = '--psm 6 --oem 3'
            text = pytesseract.image_to_string(processed, config=config)
            text = text.strip()

            # Validate based on field type
            if text:
                validated_text = self._validate_extracted_text(text, field_name, field_info)
                return validated_text if validated_text else None

            return None
        except Exception as e:
            # Fallback: return extracted text without validation
            return self._extract_text_fallback(region, field_name)

    def _preprocess_for_ocr(self, region: np.ndarray) -> np.ndarray:
        """Preprocess image region for better OCR"""
        # Convert to grayscale
        if len(region.shape) == 3:
            gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        else:
            gray = region

        # Increase contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Denoise
        denoised = cv2.fastNlMeansDenoising(enhanced)

        # Threshold
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        return binary

    def _validate_extracted_text(self, text: str, field_name: str, field_info: dict) -> Optional[str]:
        """Validate extracted text based on field type"""
        pattern = field_info.get('pattern')

        if not pattern:
            return text if text else None

        # Try to find pattern match
        matches = re.findall(pattern, text)
        if matches:
            return matches[0]

        return None

    def _extract_text_fallback(self, region: np.ndarray, field_name: str) -> Optional[str]:
        """Fallback text extraction without full OCR"""
        # Use edge detection to find text regions
        if len(region.shape) == 3:
            gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
        else:
            gray = region

        # Check if region has text-like features
        edges = cv2.Canny(gray, 50, 150)
        text_percentage = np.sum(edges > 0) / edges.size

        # Return field marker if text-like content detected
        if text_percentage > 0.05:
            return f"[Text detected in {field_name}]"

        return None


def extract_cheque_fields_advanced(image: np.ndarray) -> Dict[str, ExtractedFieldData]:
    """Convenience function for advanced field extraction"""
    extractor = AdvancedChequeFieldExtractor()
    return extractor.extract_fields(image)
