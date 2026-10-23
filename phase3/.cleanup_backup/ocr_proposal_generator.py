"""
OCR-Based Cheque Field Proposal Generator
Generates proposals using EasyOCR with full evidence recording
"""

import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class OCRProposalGenerator:
    """Generate field proposals from OCR text detection"""

    def __init__(self):
        """Initialize OCR reader"""
        try:
            import easyocr
            self.reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR initialized successfully")
            self.ocr_available = True
        except Exception as e:
            logger.warning(f"EasyOCR initialization failed: {e}")
            self.ocr_available = False
            self.reader = None

    def extract_text_regions(self, image_path: str) -> List[Dict]:
        """
        Extract text regions from image using EasyOCR

        Args:
            image_path: Path to image file

        Returns:
            List of {text, bbox, confidence} dicts from OCR
        """
        if not self.ocr_available:
            logger.warning(f"OCR not available, skipping {image_path}")
            return []

        try:
            img = cv2.imread(str(image_path))
            if img is None:
                logger.error(f"Cannot read image: {image_path}")
                return []

            # EasyOCR returns list of (bbox, text, confidence)
            # bbox is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
            results = self.reader.readtext(img, detail=1)

            height, width = img.shape[:2]
            text_regions = []

            for bbox, text, conf in results:
                # Convert bbox corners to normalized bounds
                xs = [p[0] for p in bbox]
                ys = [p[1] for p in bbox]
                x_min = min(xs) / width
                y_min = min(ys) / height
                x_max = max(xs) / width
                y_max = max(ys) / height

                region = {
                    'text': text.strip(),
                    'bbox': [x_min, y_min, x_max - x_min, y_max - y_min],
                    'confidence': float(conf),
                    'position': self._get_position_name(x_min, y_min, x_max, y_max)
                }
                text_regions.append(region)

            logger.debug(f"Extracted {len(text_regions)} text regions from {image_path}")
            return text_regions

        except Exception as e:
            logger.error(f"OCR extraction failed for {image_path}: {e}")
            return []

    def _get_position_name(self, x_min: float, y_min: float, x_max: float, y_max: float) -> str:
        """Get position descriptor for a region"""
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2

        positions = []
        if x_center < 0.4:
            positions.append("left")
        elif x_center > 0.6:
            positions.append("right")
        else:
            positions.append("center")

        if y_center < 0.3:
            positions.append("top")
        elif y_center > 0.7:
            positions.append("bottom")
        else:
            positions.append("middle")

        return "-".join(positions)

    def classify_text_to_field(self, region: Dict) -> Tuple[Optional[str], str, str]:
        """
        Classify OCR region to field with evidence

        Args:
            region: {text, bbox, confidence, position} from extract_text_regions

        Returns:
            (field_name, evidence_string, confidence_level)
        """
        text = region['text']
        position = region['position']
        conf = region['confidence']

        # Cheque number: 6-10 consecutive digits, top-right
        if self._matches_pattern(text, r'^\d{6,10}$') and position == 'right-top':
            evidence = f"Matched cheque number pattern: 6-10 digits. Text: '{text}'. Position: {position}."
            return 'cheque_number', evidence, 'high'

        # Date: d/d/yyyy or dd/dd/yyyy format, right side
        if self._matches_pattern(text, r'^\d{1,2}/\d{1,2}/\d{2,4}$') and 'right' in position:
            evidence = f"Matched date format: {text}. Position: {position}."
            return 'date', evidence, 'high'

        # Amount: numeric with optional commas/decimals, right-middle
        if self._matches_pattern(text, r'^[\d,\.]+$') and position == 'right-middle':
            if len(text) > 3:  # Avoid single digits
                evidence = f"Numeric content in amount region. Text: '{text}'. Position: {position}."
                return 'amount', evidence, 'medium'

        # MICR: exactly 9 digits, bottom
        if self._matches_pattern(text, r'^\d{9}$') and 'bottom' in position:
            evidence = f"Matched MICR pattern: 9 digits. Text: '{text}'. Position: {position}."
            return 'micr_code', evidence, 'high'

        # Bank name: text in top-left region
        if 'left' in position and 'top' in position and len(text) > 2:
            if not self._matches_pattern(text, r'^\d'):  # Not starting with digit
                evidence = f"Text in top-left region (typical bank position). Text: '{text}'."
                return 'bank_name', evidence, 'low'

        # Account number: 8-20 digits, left-middle
        if self._matches_pattern(text, r'^\d{8,20}$') and 'left' in position:
            evidence = f"Numeric content (8-20 digits) in left region. Text: '{text}'. Position: {position}."
            return 'account_number', evidence, 'low'

        # Payee name: text cluster in center, largish region
        if position == 'center-middle' and len(text) > 3:
            if not self._matches_pattern(text, r'^\d'):  # Not all digits
                evidence = f"Text cluster in center region (typical payee position). Text: '{text}'."
                return 'payee_name', evidence, 'medium'

        # No field match
        evidence = f"Detected text but no field classification match. Text: '{text}'. Position: {position}."
        return None, evidence, None

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Check if text matches regex pattern"""
        import re
        return re.match(pattern, text) is not None

    def generate_proposals(self, image_path: str) -> Dict:
        """
        Generate proposals from OCR for single image

        Args:
            image_path: Path to image

        Returns:
            {
              'field_name': {
                'box': [x_min, y_min, width, height],
                'method': 'ocr',
                'ocr_text': '<extracted_text>',
                'ocr_confidence': 0.X,
                'evidence': '<reasoning>',
                'classification_confidence': 'high|medium|low'
              },
              '_unclassified_text': [list of unmatched text]
            }
        """
        proposals = {}
        unclassified = []

        # Extract all text
        text_regions = self.extract_text_regions(image_path)
        if not text_regions:
            logger.debug(f"No text regions extracted from {image_path}")
            return proposals

        # Classify each region
        for region in text_regions:
            field_name, evidence, conf_level = self.classify_text_to_field(region)

            if field_name:
                # Accept field assignment
                if field_name not in proposals or conf_level == 'high':
                    # Keep highest confidence classification
                    proposals[field_name] = {
                        'box': region['bbox'],
                        'method': 'ocr',
                        'ocr_text': region['text'],
                        'ocr_confidence': region['confidence'],
                        'evidence': evidence,
                        'classification_confidence': conf_level
                    }
                    logger.debug(f"  {field_name}: {region['text']} ({conf_level})")
            else:
                # No field match
                unclassified.append({
                    'text': region['text'],
                    'bbox': region['bbox'],
                    'ocr_confidence': region['confidence'],
                    'evidence': evidence
                })
                logger.debug(f"  [unclassified]: {region['text']}")

        if unclassified:
            proposals['_unclassified_text'] = unclassified

        return proposals


def test_ocr_generator():
    """Test OCR proposal generation with sample image"""
    import json
    from pathlib import Path

    # Find first test image
    train_csv = Path('C:/Users/Rushmitha/OneDrive/Desktop/cheque/datasets/splits/train.csv')

    if not train_csv.exists():
        print("ERROR: train.csv not found")
        return

    # Get first image path
    with open(train_csv) as f:
        f.readline()  # Skip header
        first_line = f.readline()
        image_path = first_line.split(',')[0].strip()

    project_root = Path('C:/Users/Rushmitha/OneDrive/Desktop/cheque')
    full_path = project_root / image_path

    print(f"Testing OCR generator on: {full_path}")
    print(f"File exists: {full_path.exists()}")

    if not full_path.exists():
        print("ERROR: Image file not found")
        return

    # Generate proposals
    generator = OCRProposalGenerator()
    proposals = generator.generate_proposals(str(full_path))

    print(f"\nGenerated {len(proposals)} field proposals:")
    print(json.dumps(proposals, indent=2))

    return proposals


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    test_ocr_generator()
