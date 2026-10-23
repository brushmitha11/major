"""
Phase 3 Image Quality Assessment Module
Quality/Usability gate for cheque images
NOT a forgery detector - purely measures image usability for downstream processing
"""

import numpy as np
import cv2
from typing import Dict, Tuple


class ImageQualityAssessment:
    """
    Assess image quality across 5 dimensions:
    1. Sharpness (Laplacian variance)
    2. Contrast (histogram spread)
    3. Brightness (mean pixel value)
    4. Skew/Rotation (document alignment)
    5. Completeness (full document capture)

    Purpose: USABILITY GATE
    Not a forgery detector - measures image quality for reliable processing.
    """

    # Provisional threshold for usability (NOT validated against data)
    PROVISIONAL_QUALITY_THRESHOLD = 0.65

    # Equal weighting for all components
    SCORE_WEIGHTS = {
        'sharpness': 0.2,
        'contrast': 0.2,
        'brightness': 0.2,
        'skew': 0.2,
        'completeness': 0.2
    }

    def __init__(self):
        """Initialize quality assessment"""
        self.component_scores = {}

    def assess_sharpness(self, image: np.ndarray) -> float:
        """
        Measure image sharpness using Laplacian variance.

        Low variance = blurry
        High variance = sharp

        Args:
            image: grayscale or RGB image

        Returns:
            sharpness score in [0, 1]
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Compute Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        variance = laplacian.var()

        # Normalize to [0, 1]
        # Typical range: 0 (blurry) to 500+ (sharp)
        # Use sigmoid-like normalization: variance / (variance + 100)
        normalized_sharpness = variance / (variance + 100.0)

        return float(np.clip(normalized_sharpness, 0.0, 1.0))

    def assess_contrast(self, image: np.ndarray) -> float:
        """
        Measure image contrast using histogram spread.

        Low contrast = similar pixel values across image
        High contrast = wide spread of pixel values

        Args:
            image: grayscale or RGB image

        Returns:
            contrast score in [0, 1]
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Compute standard deviation of pixel values
        std_dev = np.std(gray)

        # Normalize to [0, 1]
        # Maximum possible std_dev ≈ 127.5 for uniform [0, 255] distribution
        # Use: std_dev / 127.5
        normalized_contrast = std_dev / 127.5

        return float(np.clip(normalized_contrast, 0.0, 1.0))

    def assess_brightness(self, image: np.ndarray) -> float:
        """
        Measure image brightness/illumination quality for document images.

        ** CORRECTED HEURISTIC FOR DOCUMENT IMAGES **
        Detects severely underexposed and severely overexposed images
        by examining histogram extremes (not mean brightness).
        Suitable for scanned cheques with white background and dark text.

        This heuristic is provisional and should be validated against the
        validation split after model training to ensure it predicts usability
        independently of genuine/forgery labels.

        Args:
            image: grayscale or RGB image

        Returns:
            brightness quality score in [0, 1]
            1.0 = well-illuminated document with good text/background separation
            lower values = severely underexposed or overexposed
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Examine histogram extremes
        very_dark_pixels = np.sum(gray < 30)
        very_bright_pixels = np.sum(gray > 240)
        total_pixels = gray.size

        very_dark_ratio = very_dark_pixels / total_pixels
        very_bright_ratio = very_bright_pixels / total_pixels

        # For well-illuminated cheque images:
        # - Should have meaningful dark content (text, borders) but not excessive
        # - Should have significant bright content (paper background)

        # PROVISIONAL thresholds (to be validated on validation split)
        min_dark_ratio = 0.01
        max_dark_ratio = 0.80
        min_bright_ratio = 0.05
        max_bright_ratio = 0.99

        # Score based on whether histogram extremes fall in reasonable ranges
        dark_in_range = min_dark_ratio <= very_dark_ratio <= max_dark_ratio
        bright_in_range = min_bright_ratio <= very_bright_ratio <= max_bright_ratio

        if dark_in_range and bright_in_range:
            score = 1.0
        elif very_dark_ratio > max_dark_ratio:
            score = 0.2
        elif very_dark_ratio < min_dark_ratio:
            score = 0.5
        elif very_bright_ratio > max_bright_ratio:
            score = 0.2
        elif very_bright_ratio < min_bright_ratio:
            score = 0.3
        else:
            score = 0.6

        return float(np.clip(score, 0.0, 1.0))

    def assess_skew(self, image: np.ndarray) -> float:
        """
        Estimate document rotation/skew using line segment detection.

        ** CORRECTED HEURISTIC FOR DOCUMENT BORDERS **
        Uses HoughLinesP to detect line segments and identifies document
        orientation from long, horizontal/vertical segments (likely borders).
        Short internal segments (text, MICR lines) are de-prioritized.

        If no reliable border-like segments are detected, returns neutral score 0.7.

        Limitation: Influenced by cheque layout elements (text, MICR lines,
        field boundaries). A production system would require dedicated training.

        Args:
            image: grayscale or RGB image

        Returns:
            skew quality score in [0, 1]
            1.0 = well-aligned (rotation < 2° from horizontal/vertical)
            0.7 = neutral (no reliable long border segments detected)
            lower values = increasing rotation detected
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Use HoughLinesP to detect line segments
        # minLineLength: minimum segment length (prioritize long borders)
        # maxLineGap: maximum gap to connect collinear segments
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=50,
            minLineLength=50,
            maxLineGap=10
        )

        if lines is None or len(lines) == 0:
            # No long line segments detected
            return 0.7

        # Compute orientation of each detected segment
        orientations = []
        lengths = []

        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Compute segment length
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            lengths.append(length)

            # Compute orientation using atan2
            dy = y2 - y1
            dx = x2 - x1
            orientation = np.degrees(np.arctan2(dy, dx))

            # Normalize to [-90°, 90°)
            while orientation < -90:
                orientation += 180
            while orientation >= 90:
                orientation -= 180

            orientations.append(orientation)

        if len(orientations) == 0:
            return 0.7

        # Weight by segment length (prioritize long segments = likely borders)
        lengths = np.array(lengths)
        weights = lengths / np.sum(lengths)

        # Compute weighted median orientation
        sorted_indices = np.argsort(orientations)
        sorted_orientations = np.array(orientations)[sorted_indices]
        sorted_weights = weights[sorted_indices]
        cumsum_weights = np.cumsum(sorted_weights)
        weighted_median = sorted_orientations[np.argmax(cumsum_weights >= 0.5)]

        # Measure deviation from nearest cardinal direction
        deviation_from_0 = abs(weighted_median)
        deviation_from_90 = abs(90 - abs(weighted_median))
        min_deviation = min(deviation_from_0, deviation_from_90)

        # Score based on deviation
        if min_deviation < 2:
            score = 1.0
        elif min_deviation < 5:
            score = 0.9
        elif min_deviation < 15:
            score = 0.6
        else:
            score = 0.2

        return float(np.clip(score, 0.0, 1.0))

    def assess_completeness(self, image: np.ndarray) -> float:
        """
        Estimate whether full cheque is captured (HEURISTIC with limitations).

        ** LIMITATION **
        Uses edge density in border regions. Isolated text/noise in borders
        may be misinterpreted as document boundaries. A reliable document-boundary
        detector would require dedicated training or more sophisticated analysis.

        Conservative approach: Require substantial edge content in borders.

        Args:
            image: grayscale or RGB image

        Returns:
            completeness score in [0, 1]
            1.0 = full document boundaries visible (presumed complete)
            lower values = missing or weak borders (likely cropped)
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        h, w = gray.shape
        border_width = int(0.1 * w)  # 10% of width
        border_height = int(0.1 * h)  # 10% of height

        # Detect edges
        edges = cv2.Canny(gray, 50, 150)

        # Count non-zero edge pixels in each border region
        top_border_count = np.count_nonzero(edges[:border_height, :])
        bottom_border_count = np.count_nonzero(edges[-border_height:, :])
        left_border_count = np.count_nonzero(edges[:, :border_width])
        right_border_count = np.count_nonzero(edges[:, -border_width:])

        # Calculate border areas
        horizontal_border_area = border_height * w
        vertical_border_area = border_width * h

        # Threshold: 5% edge-pixel density
        edge_threshold_horizontal = 0.05 * horizontal_border_area
        edge_threshold_vertical = 0.05 * vertical_border_area

        # Check if borders have substantial edge content
        top_border = top_border_count > edge_threshold_horizontal
        bottom_border = bottom_border_count > edge_threshold_horizontal
        left_border = left_border_count > edge_threshold_vertical
        right_border = right_border_count > edge_threshold_vertical

        borders_with_content = sum([top_border, bottom_border, left_border, right_border])

        # Score based on how many borders have substantial content
        completeness_scores = {4: 1.0, 3: 0.85, 2: 0.6, 1: 0.3, 0: 0.1}

        return float(completeness_scores.get(borders_with_content, 0.1))

    def compute_combined_score(self, component_scores: Dict[str, float]) -> float:
        """
        Combine component scores into single quality score.

        Formula: Equal weighted average of all components
        Quality = 0.2 * sharpness + 0.2 * contrast + 0.2 * brightness +
                  0.2 * skew + 0.2 * completeness

        Args:
            component_scores: Dict with keys ['sharpness', 'contrast', 'brightness', 'skew', 'completeness']

        Returns:
            combined score in [0, 1]
        """
        combined = 0.0

        for component, weight in self.SCORE_WEIGHTS.items():
            if component in component_scores:
                score = component_scores[component]
                combined += weight * score

        return float(np.clip(combined, 0.0, 1.0))

    def assess_image_quality(self, image: np.ndarray) -> Dict:
        """
        Comprehensive image quality assessment.

        PURPOSE: USABILITY GATE (not forgery detection)

        Args:
            image: Input image (RGB uint8)

        Returns:
            Dict with:
                - sharpness: float [0, 1]
                - contrast: float [0, 1]
                - brightness: float [0, 1]
                - skew: float [0, 1]
                - completeness: float [0, 1]
                - combined_score: float [0, 1]
                - pass_quality_gate: bool (score >= 0.65)
                - threshold_used: float (0.65, provisional)
        """
        # Compute individual metrics
        sharpness = self.assess_sharpness(image)
        contrast = self.assess_contrast(image)
        brightness = self.assess_brightness(image)
        skew = self.assess_skew(image)
        completeness = self.assess_completeness(image)

        component_scores = {
            'sharpness': sharpness,
            'contrast': contrast,
            'brightness': brightness,
            'skew': skew,
            'completeness': completeness
        }

        # Compute combined score
        combined_score = self.compute_combined_score(component_scores)

        # Determine pass/fail using PROVISIONAL threshold
        # NOT based on genuine/forgery labels
        passes_quality_gate = combined_score >= self.PROVISIONAL_QUALITY_THRESHOLD

        self.component_scores = component_scores

        return {
            'sharpness': sharpness,
            'contrast': contrast,
            'brightness': brightness,
            'skew': skew,
            'completeness': completeness,
            'combined_score': combined_score,
            'pass_quality_gate': passes_quality_gate,
            'threshold_used': self.PROVISIONAL_QUALITY_THRESHOLD
        }
