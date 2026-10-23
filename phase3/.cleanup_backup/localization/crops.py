"""
Phase 3 Field Localization — Crop Extraction

Extract field regions (amount, payee, date, signature) from cheque images
using registered/transformed bounding boxes.
"""

from dataclasses import dataclass
from typing import Optional, Tuple
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


@dataclass
class CropResult:
    """Result of extracting a single field crop"""
    field: str
    crop: Optional[np.ndarray]
    bbox_original: Tuple[int, int, int, int]
    bbox_transformed: Optional[Tuple[int, int, int, int]]
    is_valid: bool
    reason: Optional[str]


def transform_bbox(bbox_canonical: Tuple[int, int, int, int], affine_matrix: np.ndarray) -> Tuple[int, int, int, int]:
    """Transform bounding box from canonical template space to image space."""
    x_min, y_min, x_max, y_max = bbox_canonical
    corners_canonical = np.array([[x_min, y_min], [x_max, y_min], [x_max, y_max], [x_min, y_max]], dtype=np.float32)
    n_corners = len(corners_canonical)
    corners_homog = np.hstack([corners_canonical, np.ones((n_corners, 1))])
    transformed = affine_matrix @ corners_homog.T
    transformed = transformed.T
    x_coords, y_coords = transformed[:, 0], transformed[:, 1]
    x_min_new = int(np.floor(np.min(x_coords)))
    y_min_new = int(np.floor(np.min(y_coords)))
    x_max_new = int(np.ceil(np.max(x_coords)))
    y_max_new = int(np.ceil(np.max(y_coords)))
    return (x_min_new, y_min_new, x_max_new, y_max_new)


def is_bbox_valid(bbox: Tuple[int, int, int, int], image_shape: Tuple[int, int]) -> Tuple[bool, Optional[str]]:
    """Validate that bbox is fully within image bounds."""
    x_min, y_min, x_max, y_max = bbox
    height, width = image_shape

    if x_min < 0:
        return False, f"x_min={x_min} < 0"
    if y_min < 0:
        return False, f"y_min={y_min} < 0"
    if x_max > width:
        return False, f"x_max={x_max} > width={width}"
    if y_max > height:
        return False, f"y_max={y_max} > height={height}"
    if x_min >= x_max:
        return False, f"x_min={x_min} >= x_max={x_max}"
    if y_min >= y_max:
        return False, f"y_min={y_min} >= y_max={y_max}"

    area = (x_max - x_min) * (y_max - y_min)
    if area < 100:
        return False, f"Crop area={area} < 100 pixels² (engineering sanity check)"

    return True, None


def extract_crop(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> Tuple[Optional[np.ndarray], Optional[str]]:
    """Extract crop patch from image using bbox."""
    if image.ndim != 3 or image.shape[2] != 3:
        return None, f"Input image must be RGB with shape (H, W, 3), got {image.shape}"

    is_valid, reason = is_bbox_valid(bbox, image.shape[:2])
    if not is_valid:
        return None, reason

    x_min, y_min, x_max, y_max = bbox
    try:
        crop = image[y_min:y_max, x_min:x_max, :]
        if crop.size == 0:
            return None, "Extracted crop is empty"
        return crop, None
    except Exception as e:
        return None, f"Crop extraction failed: {e}"


def resize_crop(crop: Optional[np.ndarray], target_size: Tuple[int, int] = (256, 128)) -> Optional[np.ndarray]:
    """Resize crop to standard dimensions."""
    if crop is None:
        return None
    try:
        target_height, target_width = target_size
        resized = cv2.resize(crop, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
        return resized
    except Exception as e:
        logger.error(f"Crop resizing failed: {e}")
        return None


def extract_field_crop(image: np.ndarray, field_name: str, bbox_canonical: Tuple[int, int, int, int],
                       affine_matrix: Optional[np.ndarray], target_size: Tuple[int, int] = (256, 128)) -> CropResult:
    """Extract, transform, and resize a single field crop."""
    if affine_matrix is None:
        return CropResult(field=field_name, crop=None, bbox_original=bbox_canonical, bbox_transformed=None,
                         is_valid=False, reason="No affine transformation (registration failed)")

    try:
        bbox_transformed = transform_bbox(bbox_canonical, affine_matrix)
    except Exception as e:
        logger.error(f"BBox transformation failed for {field_name}: {e}")
        return CropResult(field=field_name, crop=None, bbox_original=bbox_canonical, bbox_transformed=None,
                         is_valid=False, reason=f"BBox transformation failed: {e}")

    is_valid, validation_reason = is_bbox_valid(bbox_transformed, image.shape[:2])
    if not is_valid:
        return CropResult(field=field_name, crop=None, bbox_original=bbox_canonical, bbox_transformed=bbox_transformed,
                         is_valid=False, reason=f"Transformed bbox out of bounds: {validation_reason}")

    crop, extraction_reason = extract_crop(image, bbox_transformed)
    if crop is None:
        return CropResult(field=field_name, crop=None, bbox_original=bbox_canonical, bbox_transformed=bbox_transformed,
                         is_valid=False, reason=f"Crop extraction failed: {extraction_reason}")

    resized = resize_crop(crop, target_size)
    if resized is None:
        return CropResult(field=field_name, crop=None, bbox_original=bbox_canonical, bbox_transformed=bbox_transformed,
                         is_valid=False, reason="Crop resizing failed")

    return CropResult(field=field_name, crop=resized, bbox_original=bbox_canonical, bbox_transformed=bbox_transformed,
                     is_valid=True, reason=None)
