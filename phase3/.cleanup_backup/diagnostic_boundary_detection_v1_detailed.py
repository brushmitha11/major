"""
PHASE 3 REGISTRATION V1 — DETAILED BOUNDARY DETECTION DIAGNOSTIC

Enhanced diagnostic showing per-stage results for all 4 TRAIN images.

TRAIN-only. No modification to registration.py. Investigation only.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
import pandas as pd
from localization.registration import (
    _order_corners_deterministic,
    _validate_quadrilateral_geometry,
    _assess_boundary_plausibility,
    _line_intersection,
)

# Load train CSV to find image paths
train_df = pd.read_csv("datasets/splits/train.csv")

# Get one TRAIN image per bank
TEST_IMAGES = {}
for bank in ["AXIS BANK", "CANARA BANK", "ICICI BANK", "SYNDICATE BANK"]:
    bank_df = train_df[(train_df['bank'] == bank) & (train_df['image_path'].str.contains('datasets/raw'))]
    if len(bank_df) > 0:
        TEST_IMAGES[bank] = bank_df.iloc[0]['image_path']


def analyze_stage1_contour(gray: np.ndarray, image_shape: tuple) -> dict:
    """Analyze Stage 1: Contour-based detection with plausibility."""
    h, w = image_shape

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    # Find quadrilateral candidates
    all_quads = []
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

        all_quads.append((quad_pts, contour))

    # Filter: convex + geometry
    convex_count = 0
    geometry_valid_count = 0
    geometry_valid_quads = []

    for quad_pts, contour in all_quads:
        if not cv2.isContourConvex(contour):
            continue
        convex_count += 1

        if not _validate_quadrilateral_geometry(quad_pts):
            continue
        geometry_valid_count += 1

        area = cv2.contourArea(contour)
        geometry_valid_quads.append((area, quad_pts))

    # Find largest
    if len(geometry_valid_quads) == 0:
        return {
            'total_contours': len(contours),
            'total_quadrilaterals': len(all_quads),
            'convex_count': convex_count,
            'geometry_valid_count': geometry_valid_count,
            'largest_candidate': None,
            'plausibility': "No candidates",
            'stage1_result': 'REJECTED'
        }

    geometry_valid_quads.sort(key=lambda x: x[0], reverse=True)
    largest_area, largest_quad = geometry_valid_quads[0]

    # Plausibility assessment
    assessment, evidence, reason = _assess_boundary_plausibility(
        largest_quad, image_shape, largest_area
    )

    stage1_result = 'ACCEPTED' if assessment == 'LIKELY_BOUNDARY' else 'REJECTED'

    x_coords = [c[0] for c in largest_quad]
    y_coords = [c[1] for c in largest_quad]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)

    return {
        'total_contours': len(contours),
        'total_quadrilaterals': len(all_quads),
        'convex_count': convex_count,
        'geometry_valid_count': geometry_valid_count,
        'largest_candidate': {
            'area': float(largest_area),
            'coverage_pct': 100 * largest_area / (w * h),
            'width': int(width),
            'height': int(height),
            'points': largest_quad.tolist(),
        },
        'plausibility_assessment': assessment,
        'plausibility_reason': reason,
        'plausibility_evidence': evidence,
        'stage1_result': stage1_result
    }


def analyze_stage2_hough(gray: np.ndarray, image_shape: tuple) -> dict:
    """Analyze Stage 2: Hough line detection."""
    h, w = image_shape

    edges = cv2.Canny(gray, 50, 150)

    # Hough detection
    lines = cv2.HoughLinesP(
        edges,
        rho=1.0,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=200,
        maxLineGap=20
    )

    if lines is None or len(lines) == 0:
        return {
            'lines_detected': 0,
            'horizontal_lines': 0,
            'vertical_lines': 0,
            'stage2_result': 'FAILED - No lines detected'
        }

    # Classify lines
    horizontal_lines = []
    vertical_lines = []
    ANGLE_TOLERANCE = 15.0

    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle_rad = np.arctan2(y2 - y1, x2 - x1)
        angle_deg = np.degrees(angle_rad)

        if angle_deg < 0:
            angle_deg += 180

        if abs(angle_deg) < ANGLE_TOLERANCE or abs(angle_deg - 180) < ANGLE_TOLERANCE:
            horizontal_lines.append((x1, y1, x2, y2))
        elif abs(angle_deg - 90) < ANGLE_TOLERANCE:
            vertical_lines.append((x1, y1, x2, y2))

    if len(horizontal_lines) < 2 or len(vertical_lines) < 2:
        return {
            'lines_detected': len(lines),
            'horizontal_lines': len(horizontal_lines),
            'vertical_lines': len(vertical_lines),
            'stage2_result': 'FAILED - Insufficient edges'
        }

    # Identify 4 main edges
    h_sorted = sorted(horizontal_lines, key=lambda l: (l[1] + l[3]) / 2)
    v_sorted = sorted(vertical_lines, key=lambda l: (l[0] + l[2]) / 2)

    top_line = h_sorted[0]
    bottom_line = h_sorted[-1]
    left_line = v_sorted[0]
    right_line = v_sorted[-1]

    # Compute intersections
    tl = _line_intersection(top_line, left_line)
    tr = _line_intersection(top_line, right_line)
    br = _line_intersection(bottom_line, right_line)
    bl = _line_intersection(bottom_line, left_line)

    if None in [tl, tr, br, bl]:
        return {
            'lines_detected': len(lines),
            'horizontal_lines': len(horizontal_lines),
            'vertical_lines': len(vertical_lines),
            'stage2_result': 'FAILED - Parallel lines (no intersection)'
        }

    quad_pts = np.array([tl, tr, br, bl], dtype=int)
    quad_pts[:, 0] = np.clip(quad_pts[:, 0], 0, w)
    quad_pts[:, 1] = np.clip(quad_pts[:, 1], 0, h)

    # Geometry validation
    if not _validate_quadrilateral_geometry(quad_pts):
        return {
            'lines_detected': len(lines),
            'horizontal_lines': len(horizontal_lines),
            'vertical_lines': len(vertical_lines),
            'top_line': list(top_line),
            'bottom_line': list(bottom_line),
            'left_line': list(left_line),
            'right_line': list(right_line),
            'computed_corners': [tl, tr, br, bl],
            'stage2_result': 'FAILED - Computed corners fail geometry validation'
        }

    # Plausibility assessment
    shoelace = 0.5 * abs(sum(quad_pts[i, 0] * quad_pts[(i + 1) % 4, 1] -
                              quad_pts[(i + 1) % 4, 0] * quad_pts[i, 1] for i in range(4)))

    assessment, evidence, reason = _assess_boundary_plausibility(
        quad_pts, image_shape, shoelace
    )

    stage2_result = 'ACCEPTED' if assessment in ['LIKELY_BOUNDARY', 'UNCERTAIN'] else 'REJECTED'

    x_coords = [c[0] for c in [tl, tr, br, bl]]
    y_coords = [c[1] for c in [tl, tr, br, bl]]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)

    return {
        'lines_detected': len(lines),
        'horizontal_lines': len(horizontal_lines),
        'vertical_lines': len(vertical_lines),
        'top_line': list(top_line),
        'bottom_line': list(bottom_line),
        'left_line': list(left_line),
        'right_line': list(right_line),
        'computed_corners': [tl, tr, br, bl],
        'computed_area': float(shoelace),
        'computed_coverage_pct': 100 * shoelace / (w * h),
        'computed_width': int(width),
        'computed_height': int(height),
        'plausibility_assessment': assessment,
        'plausibility_reason': reason,
        'stage2_result': stage2_result
    }


def analyze_stage3_morphological(gray: np.ndarray, image_shape: tuple) -> dict:
    """Analyze Stage 3: Morphological + contour retry."""
    h, w = image_shape

    edges = cv2.Canny(gray, 50, 150)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed_edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)

    # Contour detection
    contours, _ = cv2.findContours(closed_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) == 0:
        return {
            'morphology_operation': 'CLOSE (5x5)',
            'total_contours': 0,
            'stage3_result': 'FAILED - No contours after morphology'
        }

    # Find quadrilateral candidates
    all_quads = []
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

        all_quads.append((quad_pts, contour))

    # Filter: convex + geometry
    convex_count = 0
    geometry_valid_count = 0
    geometry_valid_quads = []

    for quad_pts, contour in all_quads:
        if not cv2.isContourConvex(contour):
            continue
        convex_count += 1

        if not _validate_quadrilateral_geometry(quad_pts):
            continue
        geometry_valid_count += 1

        area = cv2.contourArea(contour)
        geometry_valid_quads.append((area, quad_pts))

    if len(geometry_valid_quads) == 0:
        return {
            'morphology_operation': 'CLOSE (5x5)',
            'total_contours': len(contours),
            'total_quadrilaterals': len(all_quads),
            'convex_count': convex_count,
            'geometry_valid_count': geometry_valid_count,
            'stage3_result': 'FAILED - No valid quadrilaterals after morphology'
        }

    geometry_valid_quads.sort(key=lambda x: x[0], reverse=True)
    largest_area, largest_quad = geometry_valid_quads[0]

    # Plausibility assessment
    assessment, evidence, reason = _assess_boundary_plausibility(
        largest_quad, image_shape, largest_area
    )

    stage3_result = 'ACCEPTED' if assessment in ['LIKELY_BOUNDARY', 'UNCERTAIN'] else 'REJECTED'

    x_coords = [c[0] for c in largest_quad]
    y_coords = [c[1] for c in largest_quad]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)

    return {
        'morphology_operation': 'CLOSE (5x5)',
        'total_contours': len(contours),
        'total_quadrilaterals': len(all_quads),
        'convex_count': convex_count,
        'geometry_valid_count': geometry_valid_count,
        'largest_candidate': {
            'area': float(largest_area),
            'coverage_pct': 100 * largest_area / (w * h),
            'width': int(width),
            'height': int(height),
            'points': largest_quad.tolist(),
        },
        'plausibility_assessment': assessment,
        'plausibility_reason': reason,
        'stage3_result': stage3_result
    }


def analyze_bank(bank_name: str, image_path: str):
    """Comprehensive analysis of all 3 stages for a bank."""
    print("\n" + "=" * 120)
    print(f"{bank_name} — {Path(image_path).name}")
    print("=" * 120)

    if not Path(image_path).exists():
        print(f"  ERROR: Image not found at {image_path}")
        return

    image = cv2.imread(str(image_path))
    if image is None:
        print(f"  ERROR: Failed to load image")
        return

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    image_shape = (h, w)

    print(f"\n  Image dimensions: {w} × {h}")

    # STAGE 1
    print(f"\n  [STAGE 1] CONTOUR-BASED WITH PLAUSIBILITY")
    print(f"  " + "-" * 116)
    s1 = analyze_stage1_contour(gray, image_shape)
    print(f"    Total contours: {s1['total_contours']}")
    print(f"    Quadrilateral candidates: {s1['total_quadrilaterals']}")
    print(f"    Convex candidates: {s1['convex_count']}")
    print(f"    Geometry-valid candidates: {s1['geometry_valid_count']}")

    if s1['largest_candidate'] is not None:
        lc = s1['largest_candidate']
        print(f"\n    Largest candidate:")
        print(f"      Area: {lc['area']:.0f}px² ({lc['coverage_pct']:.2f}% of image)")
        print(f"      Dimensions: {lc['width']}×{lc['height']}px")
        print(f"      Points: {lc['points']}")
        print(f"\n    Plausibility Assessment:")
        print(f"      Assessment: {s1['plausibility_assessment']}")
        print(f"      Reason: {s1['plausibility_reason']}")

    print(f"\n    Stage 1 Result: {s1['stage1_result']}")

    # STAGE 2
    print(f"\n  [STAGE 2] HOUGH LINE DETECTION")
    print(f"  " + "-" * 116)
    s2 = analyze_stage2_hough(gray, image_shape)
    print(f"    Lines detected: {s2['lines_detected']}")
    print(f"    Horizontal lines: {s2['horizontal_lines']}")
    print(f"    Vertical lines: {s2['vertical_lines']}")

    if 'computed_corners' in s2:
        print(f"\n    Selected edges:")
        print(f"      Top:    {s2['top_line']}")
        print(f"      Bottom: {s2['bottom_line']}")
        print(f"      Left:   {s2['left_line']}")
        print(f"      Right:  {s2['right_line']}")
        print(f"\n    Computed corners: {s2['computed_corners']}")

        if 'computed_area' in s2:
            print(f"\n    Computed geometry:")
            print(f"      Area: {s2['computed_area']:.0f}px² ({s2['computed_coverage_pct']:.2f}% of image)")
            print(f"      Dimensions: {s2['computed_width']}×{s2['computed_height']}px")
            print(f"\n    Plausibility Assessment:")
            print(f"      Assessment: {s2['plausibility_assessment']}")
            print(f"      Reason: {s2['plausibility_reason']}")

    print(f"\n    Stage 2 Result: {s2['stage2_result']}")

    # STAGE 3
    print(f"\n  [STAGE 3] MORPHOLOGICAL + CONTOUR RETRY")
    print(f"  " + "-" * 116)
    s3 = analyze_stage3_morphological(gray, image_shape)
    print(f"    Morphology operation: {s3['morphology_operation']}")
    print(f"    Contours detected: {s3['total_contours']}")
    print(f"    Quadrilateral candidates: {s3.get('total_quadrilaterals', 'N/A')}")
    print(f"    Convex candidates: {s3.get('convex_count', 'N/A')}")
    print(f"    Geometry-valid candidates: {s3.get('geometry_valid_count', 'N/A')}")

    if s3.get('largest_candidate') is not None:
        lc = s3['largest_candidate']
        print(f"\n    Largest candidate:")
        print(f"      Area: {lc['area']:.0f}px² ({lc['coverage_pct']:.2f}% of image)")
        print(f"      Dimensions: {lc['width']}×{lc['height']}px")
        print(f"\n    Plausibility Assessment:")
        print(f"      Assessment: {s3['plausibility_assessment']}")
        print(f"      Reason: {s3['plausibility_reason']}")

    print(f"\n    Stage 3 Result: {s3['stage3_result']}")

    # FINAL RESULT
    print(f"\n  [FINAL RESULT]")
    print(f"  " + "-" * 116)

    if s1['stage1_result'] == 'ACCEPTED':
        print(f"    Detection method: STAGE 1 (Contour-based)")
        if s1['largest_candidate']:
            print(f"    Region: {s1['largest_candidate']['width']}×{s1['largest_candidate']['height']}px")
            print(f"    Coverage: {s1['largest_candidate']['coverage_pct']:.2f}%")
    elif 'computed_corners' in s2 and s2['stage2_result'] == 'ACCEPTED':
        print(f"    Detection method: STAGE 2 (Hough lines)")
        print(f"    Region: {s2['computed_width']}×{s2['computed_height']}px")
        print(f"    Coverage: {s2['computed_coverage_pct']:.2f}%")
        print(f"    Corners: {s2['computed_corners']}")
    elif s3.get('stage3_result') == 'ACCEPTED':
        print(f"    Detection method: STAGE 3 (Morphological + contour)")
        if s3.get('largest_candidate'):
            print(f"    Region: {s3['largest_candidate']['width']}×{s3['largest_candidate']['height']}px")
            print(f"    Coverage: {s3['largest_candidate']['coverage_pct']:.2f}%")
    else:
        print(f"    ✗ DETECTION FAILED")
        print(f"    All stages exhausted without finding acceptable boundary")


def main():
    print("\n" + "=" * 120)
    print("PHASE 3 REGISTRATION V1 — DETAILED BOUNDARY DETECTION DIAGNOSTIC (TRAIN ONLY)")
    print("=" * 120)
    print(f"\nDetailed per-stage analysis for 4 representative TRAIN images...")
    print(f"No validation or test data accessed. Investigation only.\n")

    for bank_name, image_path in TEST_IMAGES.items():
        analyze_bank(bank_name, image_path)

    print("\n" + "=" * 120)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 120)


if __name__ == "__main__":
    main()
