"""
Phase 3 Field Localization — Image-to-Template Registration

Aligns cheque images to bank-specific templates via corner detection and affine
transformation. Computes registration quality metrics (residual, confidence).

PROVISIONAL PARAMETERS (NOT VALIDATED):
- Residual tolerance: 10.0 pixels (diagnostic only)
- Scale range: [0.5, 2.0] (diagnostic warning only, not hard rejection)
- Rotation tolerance: 10.0° (diagnostic only)

Data Protection: TRAIN data only for development. TEST data completely protected.
"""

import numpy as np
import cv2
from typing import Tuple, List, Optional, Dict
import logging

logger = logging.getLogger(__name__)


def detect_cheque_corners(image: np.ndarray) -> Optional[List[Tuple[int, int]]]:
    """
    Detect cheque corners using multi-stage boundary-detection pipeline (V1).

    STAGE 1: Contour-based detection with plausibility assessment
    STAGE 2: Hough line detection (if Stage 1 uncertain/implausible)
    STAGE 3: Morphological + contour retry with plausibility (if Stage 2 fails)

    Returns:
        List of 4 corners in order [TL, TR, BR, BL], or None if all stages fail

    Design: REGISTRATION_V1_FINAL_DESIGN.md
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image

        h, w = gray.shape

        # STAGE 1: Contour-based detection with plausibility
        logger.debug("Stage 1: Contour-based detection with plausibility assessment")
        corners = _detect_corners_stage1_contour(gray, (h, w))
        if corners is not None:
            logger.info("Boundary detected by Stage 1 (contour-based)")
            return corners

        logger.debug("Stage 1 failed or implausible; attempting Stage 2 (Hough lines)")

        # STAGE 2: Hough line detection
        corners = _detect_corners_stage2_hough(gray, (h, w))
        if corners is not None:
            logger.info("Boundary detected by Stage 2 (Hough lines)")
            return corners

        logger.debug("Stage 2 failed; attempting Stage 3 (morphological + contour)")

        # STAGE 3: Morphological + contour retry with plausibility
        corners = _detect_corners_stage3_morphological(gray, (h, w))
        if corners is not None:
            logger.info("Boundary detected by Stage 3 (morphological + contour)")
            return corners

        logger.warning("All boundary detection stages failed. Registration will fail.")
        return None

    except Exception as e:
        logger.error(f"Corner detection pipeline failed: {e}")
        return None


def _detect_corners_stage1_contour(gray: np.ndarray, image_shape: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """
    STAGE 1: Contour-based detection with plausibility assessment.

    Strategy:
    1. Canny edge detection
    2. Find contours and approximate to quadrilaterals
    3. Filter: convex + geometry validation
    4. Select largest by area
    5. Assess plausibility (area coverage, boundary proximity, aspect ratio)
    6. Return if plausible; else continue to Stage 2
    """
    h, w = image_shape

    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        logger.debug("Stage 1: No contours detected")
        return None

    candidates = []
    for contour in contours:
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) != 4:
            continue

        quad_pts = approx.squeeze().astype(int)
        if quad_pts.ndim == 1:
            quad_pts = quad_pts.reshape(1, -1)
        if quad_pts.shape[0] != 4:
            continue

        area = cv2.contourArea(contour)
        is_convex = cv2.isContourConvex(contour)

        if not is_convex:
            continue
        if not _validate_quadrilateral_geometry(quad_pts):
            continue

        candidates.append((area, quad_pts))

    if len(candidates) == 0:
        logger.debug("Stage 1: No valid convex quadrilaterals found")
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    largest_area, largest_quad = candidates[0]

    # Plausibility assessment
    assessment, evidence, reason = _assess_boundary_plausibility(
        largest_quad, image_shape, largest_area
    )

    logger.debug(f"Stage 1 plausibility: {assessment} — {reason}")

    if assessment == "LIKELY_BOUNDARY":
        ordered_corners = _order_corners_deterministic(largest_quad)
        if ordered_corners is None or len(ordered_corners) < 4:
            logger.debug("Stage 1: Failed to order corners deterministically")
            return None
        return ordered_corners
    else:
        logger.debug(f"Stage 1: Candidate is {assessment}, proceeding to Stage 2")
        return None


def _assess_boundary_plausibility(
    quad_pts: np.ndarray,
    image_shape: Tuple[int, int],
    candidate_area: float
) -> Tuple[str, Dict, str]:
    """
    Assess whether a geometry-validated quadrilateral is likely a document boundary.

    Evidence-based assessment (no hard thresholds):
    - Area coverage: Is candidate area substantial relative to image?
    - Boundary proximity: Are corners close to image edges?
    - Aspect ratio consistency: Does candidate AR match image AR?

    Returns:
        (assessment, evidence_dict, reason)
        assessment: "LIKELY_BOUNDARY", "UNCERTAIN", or "LIKELY_ARTIFACT"
    """
    h, w = image_shape
    image_area = w * h
    image_ar = w / h

    # Evidence 1: Area coverage
    area_coverage_pct = 100.0 * candidate_area / image_area

    # Evidence 2: Boundary proximity
    ordered = _order_corners_deterministic(quad_pts)
    if ordered is None:
        return "LIKELY_ARTIFACT", {}, "Failed to order corners"

    tl, tr, br, bl = ordered
    boundary_distances = [
        min(tl[0], tl[1]),                          # TL: min distance to top/left edge
        min(w - tr[0], tr[1]),                      # TR: min distance to top/right edge
        min(w - br[0], h - br[1]),                  # BR: min distance to bottom/right edge
        min(bl[0], h - bl[1])                       # BL: min distance to bottom/left edge
    ]

    has_boundary_proximity = any(d < 0.2 * max(w, h) for d in boundary_distances)

    # Evidence 3: Aspect ratio consistency
    x_coords = np.array([c[0] for c in ordered], dtype=float)
    y_coords = np.array([c[1] for c in ordered], dtype=float)
    candidate_width = max(x_coords) - min(x_coords)
    candidate_height = max(y_coords) - min(y_coords)

    if candidate_height < 1e-6:
        return "LIKELY_ARTIFACT", {}, "Degenerate height"

    candidate_ar = candidate_width / candidate_height
    ar_ratio = candidate_ar / image_ar if image_ar > 0 else 1.0
    ar_diff = abs(np.log(ar_ratio))
    aspect_ratio_consistent = ar_diff < 1.0

    evidence = {
        'area_coverage_pct': float(area_coverage_pct),
        'has_boundary_proximity': bool(has_boundary_proximity),
        'boundary_distances': [float(d) for d in boundary_distances],
        'aspect_ratio_diff': float(ar_diff),
        'aspect_ratio_consistent': bool(aspect_ratio_consistent),
    }

    # Qualitative assessment: combine evidence
    strong_metrics = sum([
        area_coverage_pct > 2.0,      # At least 2-3% coverage
        has_boundary_proximity,        # Corners near boundary
        aspect_ratio_consistent        # AR consistent
    ])

    if strong_metrics >= 3:
        return "LIKELY_BOUNDARY", evidence, \
               f"All evidence strong: coverage={area_coverage_pct:.1f}%, proximity={has_boundary_proximity}, AR_ok={aspect_ratio_consistent}"
    elif strong_metrics == 2:
        return "UNCERTAIN", evidence, \
               f"Two evidence strong: coverage={area_coverage_pct:.1f}%, proximity={has_boundary_proximity}, AR_ok={aspect_ratio_consistent}"
    else:
        return "LIKELY_ARTIFACT", evidence, \
               f"Likely internal artifact: coverage={area_coverage_pct:.1f}%, proximity={has_boundary_proximity}, AR_ok={aspect_ratio_consistent}"


def _detect_corners_stage2_hough(gray: np.ndarray, image_shape: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """
    STAGE 2: Hough line-based boundary detection.

    Strategy:
    1. Canny edge detection
    2. Hough line detection (allow ±15° skew)
    3. Classify lines as horizontal/vertical
    4. Identify 4 main edges (top, bottom, left, right)
    5. Compute corner intersections
    6. Apply geometry validation + plausibility assessment

    PROVISIONAL PARAMETERS (UNVALIDATED, TRAIN-DEVELOPMENT ONLY):
    - rho=1.0, theta=π/180, threshold=100, minLineLength=200, maxLineGap=20
    - angle_tolerance=±15°
    """
    h, w = image_shape

    edges = cv2.Canny(gray, 50, 150)

    # Detect lines using Hough
    lines = cv2.HoughLinesP(
        edges,
        rho=1.0,
        theta=np.pi / 180,
        threshold=100,               # PROVISIONAL
        minLineLength=200,           # PROVISIONAL
        maxLineGap=20                # PROVISIONAL
    )

    if lines is None or len(lines) == 0:
        logger.debug("Stage 2: No lines detected by Hough")
        return None

    # Classify lines by orientation (±15° tolerance for skew)
    horizontal_lines = []
    vertical_lines = []

    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle_rad = np.arctan2(y2 - y1, x2 - x1)
        angle_deg = np.degrees(angle_rad)

        # Normalize to [0, 180)
        if angle_deg < 0:
            angle_deg += 180

        # Classify with ±15° tolerance (PROVISIONAL)
        ANGLE_TOLERANCE = 15.0

        if abs(angle_deg) < ANGLE_TOLERANCE or abs(angle_deg - 180) < ANGLE_TOLERANCE:
            horizontal_lines.append((x1, y1, x2, y2))
        elif abs(angle_deg - 90) < ANGLE_TOLERANCE:
            vertical_lines.append((x1, y1, x2, y2))

    logger.debug(f"Stage 2: Detected {len(horizontal_lines)} horizontal, {len(vertical_lines)} vertical lines")

    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        logger.debug("Stage 2: Insufficient horizontal or vertical lines")
        return None

    # Identify 4 main edges
    h_sorted_by_y = sorted(horizontal_lines, key=lambda l: (l[1] + l[3]) / 2)
    v_sorted_by_x = sorted(vertical_lines, key=lambda l: (l[0] + l[2]) / 2)

    top_line = h_sorted_by_y[0]
    bottom_line = h_sorted_by_y[-1]
    left_line = v_sorted_by_x[0]
    right_line = v_sorted_by_x[-1]

    # Compute corner intersections
    tl = _line_intersection(top_line, left_line)
    tr = _line_intersection(top_line, right_line)
    br = _line_intersection(bottom_line, right_line)
    bl = _line_intersection(bottom_line, left_line)

    if None in [tl, tr, br, bl]:
        logger.debug("Stage 2: Failed to compute all corner intersections")
        return None

    quad_pts = np.array([tl, tr, br, bl], dtype=int)

    # Clip to image bounds
    quad_pts[:, 0] = np.clip(quad_pts[:, 0], 0, w)
    quad_pts[:, 1] = np.clip(quad_pts[:, 1], 0, h)

    # Geometry validation
    if not _validate_quadrilateral_geometry(quad_pts):
        logger.debug("Stage 2: Computed corners fail geometry validation")
        return None

    # Plausibility assessment — compute area using shoelace formula
    x_coords = quad_pts[:, 0].astype(float)
    y_coords = quad_pts[:, 1].astype(float)
    candidate_area = 0.5 * abs(sum(x_coords[i] * y_coords[(i + 1) % 4] - x_coords[(i + 1) % 4] * y_coords[i] for i in range(4)))

    assessment, evidence, reason = _assess_boundary_plausibility(
        quad_pts, image_shape, candidate_area
    )

    logger.debug(f"Stage 2 plausibility: {assessment} — {reason}")

    # Accept if plausible or uncertain (final attempt)
    if assessment in ["LIKELY_BOUNDARY", "UNCERTAIN"]:
        ordered_corners = _order_corners_deterministic(quad_pts)
        if ordered_corners is None or len(ordered_corners) < 4:
            logger.debug("Stage 2: Failed to order corners deterministically")
            return None
        return ordered_corners
    else:
        logger.debug("Stage 2: Candidate is likely artifact")
        return None


def _line_intersection(line1: Tuple[int, int, int, int],
                       line2: Tuple[int, int, int, int]) -> Optional[Tuple[int, int]]:
    """
    Compute intersection of two infinite lines.

    Line format: (x1, y1, x2, y2)
    Returns: (x, y) as integers, or None if parallel
    """
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2

    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-6:
        return None  # Parallel lines

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom

    px = x1 + t * (x2 - x1)
    py = y1 + t * (y2 - y1)

    return (int(round(px)), int(round(py)))


def _detect_corners_stage3_morphological(gray: np.ndarray, image_shape: Tuple[int, int]) -> Optional[List[Tuple[int, int]]]:
    """
    STAGE 3: Morphological processing + contour retry with plausibility assessment.

    Strategy:
    1. Canny edge detection
    2. Morphological closing (fill gaps in edges)
    3. Contour detection and filtering
    4. Select largest by area
    5. Apply geometry validation + plausibility assessment
    6. Return if plausible or uncertain; else fail
    """
    h, w = image_shape

    edges = cv2.Canny(gray, 50, 150)

    # Morphological closing to connect broken edges
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Contour detection
    contours, _ = cv2.findContours(closed_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        logger.debug("Stage 3: No contours detected after morphology")
        return None

    candidates = []
    for contour in contours:
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        if len(approx) != 4:
            continue

        quad_pts = approx.squeeze().astype(int)
        if quad_pts.ndim == 1:
            quad_pts = quad_pts.reshape(1, -1)
        if quad_pts.shape[0] != 4:
            continue

        area = cv2.contourArea(contour)
        is_convex = cv2.isContourConvex(contour)

        if not is_convex:
            continue
        if not _validate_quadrilateral_geometry(quad_pts):
            continue

        candidates.append((area, quad_pts))

    if len(candidates) == 0:
        logger.debug("Stage 3: No valid convex quadrilaterals found after morphology")
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    largest_area, largest_quad = candidates[0]

    # Plausibility assessment
    assessment, evidence, reason = _assess_boundary_plausibility(
        largest_quad, image_shape, largest_area
    )

    logger.debug(f"Stage 3 plausibility: {assessment} — {reason}")

    # Accept if plausible or uncertain (this is the final attempt)
    if assessment in ["LIKELY_BOUNDARY", "UNCERTAIN"]:
        ordered_corners = _order_corners_deterministic(largest_quad)
        if ordered_corners is None or len(ordered_corners) < 4:
            logger.debug("Stage 3: Failed to order corners deterministically")
            return None
        return ordered_corners
    else:
        logger.debug("Stage 3: Candidate is likely artifact; all stages exhausted")
        return None


def _validate_quadrilateral_geometry(quad_pts: np.ndarray) -> bool:
    """
    Validate that four points form a valid quadrilateral.

    ENGINEERING SANITY CHECKS (NOT validated cheque-specific thresholds):
    - Exactly 4 distinct points
    - Sufficient spatial separation (10 pixels is a numerical safeguard only)
    - Non-zero area (100 pixels² is an engineering lower bound only)
    """
    if quad_pts.shape[0] != 4:
        return False

    quad_pts = np.array(quad_pts, dtype=float)
    min_separation = 10
    for i in range(4):
        for j in range(i + 1, 4):
            dist = np.linalg.norm(quad_pts[i] - quad_pts[j])
            if dist < min_separation:
                return False

    min_area = 100
    x, y = quad_pts[:, 0], quad_pts[:, 1]
    area = 0.5 * abs(sum(x[i] * y[(i + 1) % 4] - x[(i + 1) % 4] * y[i] for i in range(4)))

    if area < min_area:
        return False

    return True


def compute_candidate_score(
    quad_pts: np.ndarray,
    image_shape: Tuple[int, int],
    candidate_area: float
) -> float:
    """
    Rank quadrilateral candidate using 3 resolution-independent components.

    Components (weighted):
    1. Corner proximity (0.50): detected corners align with expected image corners
    2. Area coverage (0.30): candidate area relative to image area
    3. Shape consistency (0.20): candidate aspect ratio similarity to image aspect ratio

    Combined: 0.50*corner + 0.30*area + 0.20*shape

    All components: continuous [0,1], no hard rejection thresholds.
    Engineering weights only, not validated against data.
    """
    h, w = image_shape
    image_diagonal = np.sqrt(w**2 + h**2)

    # Deterministically order detected corners as TL, TR, BR, BL
    ordered_corners = _order_corners_deterministic(quad_pts)
    if ordered_corners is None:
        return 0.0

    # ========== COMPONENT 1: Corner Proximity (weight 0.50) ==========
    # Expected image corners in order: TL, TR, BR, BL
    expected_corners = np.array([
        [0, 0],        # TL
        [w, 0],        # TR
        [w, h],        # BR
        [0, h]         # BL
    ], dtype=float)

    # One-to-one correspondence comparison (ordered pair by pair)
    detected_array = np.array(ordered_corners, dtype=float)
    corner_distances = np.linalg.norm(detected_array - expected_corners, axis=1)
    mean_corner_distance = np.mean(corner_distances)

    # Normalize by image diagonal (resolution-independent)
    corner_proximity = 1.0 - (mean_corner_distance / image_diagonal)
    corner_proximity = np.clip(corner_proximity, 0.0, 1.0)

    # ========== COMPONENT 2: Area Coverage (weight 0.30) ==========
    # Candidate area as fraction of total image area
    # No arbitrary target (60%, 80%, etc.)
    image_area = w * h
    area_coverage = candidate_area / image_area
    area_coverage = np.clip(area_coverage, 0.0, 1.0)

    # ========== COMPONENT 3: Shape Consistency (weight 0.20) ==========
    # Compare candidate aspect ratio to image aspect ratio
    # Soft ranking signal only; no hard rejection threshold

    # Image aspect ratio
    image_ar = w / h

    # Candidate aspect ratio
    x_coords = np.array([c[0] for c in ordered_corners], dtype=float)
    y_coords = np.array([c[1] for c in ordered_corners], dtype=float)

    candidate_width = max(x_coords) - min(x_coords)
    candidate_height = max(y_coords) - min(y_coords)

    if candidate_height < 1e-6:
        # Degenerate case: zero height
        shape_consistency = 0.0
    else:
        candidate_ar = candidate_width / candidate_height

        # Aspect ratio difference (normalized)
        # Compare: how close is candidate AR to image AR?
        ar_ratio = candidate_ar / image_ar if image_ar > 0 else 1.0

        # Convert ratio difference to continuous [0,1] score
        # ar_ratio = 1.0 → perfect match → score = 1.0
        # ar_ratio far from 1.0 → poor match → score → 0.0

        # Formula: shape_score = 1.0 - |log(ar_ratio)| / log(2.0)
        # This normalizes by log(2.0) to keep most reasonable candidates > 0.5
        ar_difference = abs(np.log(ar_ratio)) / np.log(2.0)
        shape_consistency = 1.0 - ar_difference
        shape_consistency = np.clip(shape_consistency, 0.0, 1.0)

    # ========== COMBINED RANKING SCORE ==========
    # Weighted average of three components
    combined = (
        0.50 * corner_proximity +
        0.30 * area_coverage +
        0.20 * shape_consistency
    )

    return float(np.clip(combined, 0.0, 1.0))


def _order_corners_deterministic(corners: np.ndarray) -> Optional[List[Tuple[int, int]]]:
    """Order corners deterministically: TL, TR, BR, BL."""
    if len(corners) < 4:
        return None

    corners = np.array(corners, dtype=float)
    s = corners[:, 0] + corners[:, 1]
    d = corners[:, 1] - corners[:, 0]

    tl_idx = np.argmin(s)
    tr_idx = np.argmin(d)
    br_idx = np.argmax(s)
    bl_idx = np.argmax(d)

    indices = [tl_idx, tr_idx, br_idx, bl_idx]
    if len(set(indices)) < 4:
        logger.warning("Corner ordering produced duplicate indices")
        return None

    ordered = [
        tuple(corners[tl_idx].astype(int)),
        tuple(corners[tr_idx].astype(int)),
        tuple(corners[br_idx].astype(int)),
        tuple(corners[bl_idx].astype(int)),
    ]

    if not _validate_non_collinear(ordered[:3]):
        logger.warning("First 3 corners are collinear")
        return None

    return ordered


def _validate_non_collinear(points: List[Tuple[int, int]]) -> bool:
    """Check if 3 points are non-collinear."""
    if len(points) < 3:
        return False

    p0, p1, p2 = np.array(points[:3], dtype=float)
    v1 = p1 - p0
    v2 = p2 - p0
    cross = v1[0] * v2[1] - v1[1] * v2[0]

    return abs(cross) > 1.0


def compute_affine_transform(src_pts, dst_pts) -> Tuple[Optional[np.ndarray], Optional[float], Optional[Dict]]:
    """Compute affine transformation from source to destination points."""
    try:
        src_pts = np.array(src_pts, dtype=np.float32)
        dst_pts = np.array(dst_pts, dtype=np.float32)

        if len(src_pts) < 3 or len(dst_pts) < 3:
            logger.warning(f"Insufficient correspondences: {len(src_pts)}")
            return None, None, None

        if not _validate_non_collinear(src_pts.tolist()):
            logger.warning("Source points are collinear")
            return None, None, None

        if not _validate_non_collinear(dst_pts.tolist()):
            logger.warning("Destination points are collinear")
            return None, None, None

        if len(src_pts) == 3:
            affine_matrix = cv2.getAffineTransform(src_pts, dst_pts)
        else:
            affine_matrix, _ = cv2.estimateAffine2D(src_pts, dst_pts)
            if affine_matrix is None:
                logger.warning("cv2.estimateAffine2D() returned None")
                return None, None, None

        is_valid, reason = validate_affine_transform(affine_matrix)
        if not is_valid:
            logger.warning(f"Affine matrix validation failed: {reason}")
            return None, None, None

        residual = _compute_rmse_residual(src_pts, dst_pts, affine_matrix)
        diagnostics = _extract_transform_params(affine_matrix)

        return affine_matrix, residual, diagnostics

    except Exception as e:
        logger.error(f"Affine transformation failed: {e}")
        return None, None, None


def _compute_rmse_residual(src_pts: np.ndarray, dst_pts: np.ndarray, affine_matrix: np.ndarray) -> float:
    """Compute Root Mean Squared Error (RMSE) residual after transformation."""
    try:
        n = len(src_pts)
        src_homog = np.hstack([src_pts, np.ones((n, 1))])
        transformed = affine_matrix @ src_homog.T
        transformed = transformed.T
        distances = np.linalg.norm(transformed - dst_pts, axis=1)
        rmse = np.sqrt(np.mean(distances ** 2))
        return float(rmse)
    except Exception as e:
        logger.error(f"RMSE computation failed: {e}")
        return float('inf')


def _extract_transform_params(affine_matrix: np.ndarray) -> Dict:
    """Extract scale and rotation parameters from affine matrix."""
    try:
        a, b, tx = affine_matrix[0]
        c, d, ty = affine_matrix[1]
        sx = np.sqrt(a**2 + c**2)
        sy = np.sqrt(b**2 + d**2)
        rotation_rad = np.arctan2(c, a)
        rotation_deg = np.degrees(rotation_rad)
        return {
            'sx': float(sx),
            'sy': float(sy),
            'rotation_deg': float(rotation_deg),
            'translation': (float(tx), float(ty))
        }
    except Exception as e:
        logger.error(f"Transform parameter extraction failed: {e}")
        return {}


def compute_confidence_from_residual(residual: float, rotation_deg: float = 0.0,
                                     scale_factors: Tuple[float, float] = (1.0, 1.0),
                                     tolerance_pixels: float = 10.0) -> float:
    """
    Compute localization confidence from registration quality metrics.

    PROVISIONAL PARAMETERS (NOT VALIDATED):
    - tolerance_pixels = 10.0 (diagnostic baseline only)
    - rotation tolerance = 10.0° (diagnostic warning only)
    - scale range [0.5, 2.0] (diagnostic warning only)

    Confidence represents registration quality, not a decision criterion.
    """
    confidence = max(0.0, 1.0 - (residual / tolerance_pixels))

    if abs(rotation_deg) > 10.0:
        rotation_penalty = 0.7 * (1.0 - min(1.0, abs(rotation_deg) / 45.0))
        confidence *= rotation_penalty

    sx, sy = scale_factors
    if sx < 0.5 or sx > 2.0 or sy < 0.5 or sy > 2.0:
        logger.warning(
            f"Scale factors outside [0.5, 2.0]: sx={sx:.2f}, sy={sy:.2f} "
            "(PROVISIONAL diagnostic warning only, not hard rejection)"
        )

    return float(np.clip(confidence, 0.0, 1.0))


def validate_affine_transform(affine_matrix: np.ndarray) -> Tuple[bool, Optional[str]]:
    """Validate affine transformation matrix for degeneracy and invertibility."""
    try:
        if affine_matrix is None:
            return False, "Matrix is None"
        if affine_matrix.shape != (2, 3):
            return False, f"Invalid shape: {affine_matrix.shape} (expected 2x3)"
        det = np.linalg.det(affine_matrix[:2, :2])
        if abs(det) < 1e-6:
            return False, f"Singular matrix (det={det:.6f})"
        return True, None
    except Exception as e:
        return False, f"Validation error: {e}"
