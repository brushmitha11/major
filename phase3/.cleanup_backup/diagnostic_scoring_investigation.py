"""
Deep diagnostic investigation of scoring and candidate selection.

Analyzes:
1. Top 10 candidates by composite score for Axis/Syndicate
2. Filtering stages for Canara/ICICI
3. Why tiny regions beat larger candidates
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
import pandas as pd
from localization.registration import (
    compute_candidate_score,
    _validate_quadrilateral_geometry,
    _order_corners_deterministic,
)

# Load train CSV to find image paths
train_df = pd.read_csv("datasets/splits/train.csv")

# Get one TRAIN image per bank (the raw/original ones)
TEST_IMAGES = {}
for bank in ["AXIS BANK", "CANARA BANK", "ICICI BANK", "SYNDICATE BANK"]:
    bank_df = train_df[(train_df['bank'] == bank) & (train_df['image_path'].str.contains('datasets/raw'))]
    if len(bank_df) > 0:
        TEST_IMAGES[bank] = bank_df.iloc[0]['image_path']


def analyze_bank(bank_name: str, image_path: str):
    """Detailed analysis of candidate selection for a bank."""
    print("\n" + "=" * 80)
    print(f"{bank_name} — {image_path}")
    print("=" * 80)

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

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    print(f"  Total contours found: {len(contours)}")

    # Stage 1: All 4-point candidates
    all_4pt_candidates = []
    for idx, contour in enumerate(contours):
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
        all_4pt_candidates.append({
            'contour_idx': idx,
            'quad_pts': quad_pts,
            'area': area,
            'is_convex': is_convex,
        })

    print(f"  4-point candidates (before convexity filter): {len(all_4pt_candidates)}")

    # Stage 2: After convexity filter
    convex_candidates = [c for c in all_4pt_candidates if c['is_convex']]
    print(f"  After convexity filter: {len(convex_candidates)}")
    rejected_by_convexity = len(all_4pt_candidates) - len(convex_candidates)

    # Stage 3: After geometry validation
    geometry_valid = []
    for c in convex_candidates:
        if _validate_quadrilateral_geometry(c['quad_pts']):
            geometry_valid.append(c)

    print(f"  After geometry validation: {len(geometry_valid)}")
    rejected_by_geometry = len(convex_candidates) - len(geometry_valid)

    print(f"\n  Rejections:")
    print(f"    By convexity: {rejected_by_convexity}")
    print(f"    By geometry: {rejected_by_geometry}")

    if len(all_4pt_candidates) == 0:
        print("\n  *** NO 4-POINT CANDIDATES FOUND ***")
        return

    # For banks with failures, show top 10 BEFORE convexity filter
    if bank_name in ["CANARA", "ICICI"]:
        print(f"\n  TOP 10 CANDIDATES BEFORE CONVEXITY FILTER:")
        sorted_by_area = sorted(all_4pt_candidates, key=lambda x: x['area'], reverse=True)
        for rank, c in enumerate(sorted_by_area[:10], 1):
            pts = c['quad_pts']
            area = c['area']
            convex = "CONVEX" if c['is_convex'] else "NON-CONVEX"
            width = max(pts[:, 0]) - min(pts[:, 0])
            height = max(pts[:, 1]) - min(pts[:, 1])
            print(f"    [{rank}] Area={area:.0f}px, {convex}, {width}×{height}px")
            print(f"         Points: {pts.tolist()}")

    # For successful banks, compute scores for all valid candidates
    if len(geometry_valid) == 0:
        print("\n  *** NO VALID CANDIDATES AFTER ALL FILTERS ***")
        return

    # Compute composite scores
    candidates_with_scores = []
    for c in geometry_valid:
        quad_pts = c['quad_pts']
        area = c['area']

        # Compute individual score components
        ordered = _order_corners_deterministic(quad_pts)
        if ordered is None:
            continue

        # Component 1: Corner proximity
        image_diagonal = np.sqrt(w**2 + h**2)
        expected_corners = np.array([
            [0, 0], [w, 0], [w, h], [0, h]
        ], dtype=float)
        detected_array = np.array(ordered, dtype=float)
        corner_distances = np.linalg.norm(detected_array - expected_corners, axis=1)
        mean_corner_distance = np.mean(corner_distances)
        corner_proximity = 1.0 - (mean_corner_distance / image_diagonal)
        corner_proximity = np.clip(corner_proximity, 0.0, 1.0)

        # Component 2: Area coverage
        image_area = w * h
        area_coverage = area / image_area
        area_coverage = np.clip(area_coverage, 0.0, 1.0)

        # Component 3: Shape consistency
        image_ar = w / h
        x_coords = np.array([c[0] for c in ordered], dtype=float)
        y_coords = np.array([c[1] for c in ordered], dtype=float)
        candidate_width = max(x_coords) - min(x_coords)
        candidate_height = max(y_coords) - min(y_coords)

        if candidate_height < 1e-6:
            shape_consistency = 0.0
        else:
            candidate_ar = candidate_width / candidate_height
            ar_ratio = candidate_ar / image_ar if image_ar > 0 else 1.0
            ar_difference = abs(np.log(ar_ratio)) / np.log(2.0)
            shape_consistency = 1.0 - ar_difference
            shape_consistency = np.clip(shape_consistency, 0.0, 1.0)

        # Composite score
        composite = (
            0.50 * corner_proximity +
            0.30 * area_coverage +
            0.20 * shape_consistency
        )
        composite = np.clip(composite, 0.0, 1.0)

        candidates_with_scores.append({
            'quad_pts': quad_pts,
            'area': area,
            'corner_proximity': corner_proximity,
            'area_coverage': area_coverage,
            'shape_consistency': shape_consistency,
            'composite_score': composite,
            'ordered_corners': ordered,
            'candidate_width': candidate_width,
            'candidate_height': candidate_height,
        })

    if len(candidates_with_scores) == 0:
        print("\n  *** FAILED TO COMPUTE SCORES ***")
        return

    # Sort by composite score
    sorted_by_score = sorted(candidates_with_scores, key=lambda x: x['composite_score'], reverse=True)

    print(f"\n  TOP 10 QUADRILATERAL CANDIDATES BY COMPOSITE SCORE:")
    for rank, c in enumerate(sorted_by_score[:10], 1):
        pts = c['quad_pts']
        area = c['area']
        width = c['candidate_width']
        height = c['candidate_height']

        print(f"\n    [{rank}] COMPOSITE SCORE: {c['composite_score']:.4f}")
        print(f"         Area: {area:.0f}px ({c['area_coverage']*100:.1f}% of image)")
        print(f"         Dimensions: {width:.0f}×{height:.0f}px")
        print(f"         Corner proximity: {c['corner_proximity']:.4f}")
        print(f"         Area coverage: {c['area_coverage']:.4f}")
        print(f"         Shape consistency: {c['shape_consistency']:.4f}")
        print(f"         Corners (TL, TR, BR, BL): {c['ordered_corners']}")
        print(f"         Raw quad points: {pts.tolist()}")

    # Check which candidate is currently being selected
    sorted_by_area = sorted(candidates_with_scores, key=lambda x: x['area'], reverse=True)
    selected = sorted_by_area[0]

    print(f"\n  CURRENT SELECTION (largest by area):")
    print(f"    Area: {selected['area']:.0f}px ({selected['area_coverage']*100:.1f}% of image)")
    print(f"    Dimensions: {selected['candidate_width']:.0f}×{selected['candidate_height']:.0f}px")
    print(f"    Composite score: {selected['composite_score']:.4f}")

    # Find rank by score
    rank_by_score = next((i+1 for i, c in enumerate(sorted_by_score) if c['area'] == selected['area']), -1)
    print(f"    Rank by composite score: {rank_by_score}")

    # Identify discrepancy
    best_by_score = sorted_by_score[0]
    if abs(selected['area'] - best_by_score['area']) > 1:
        print(f"\n  *** DISCREPANCY DETECTED ***")
        print(f"    Selected (by area): Area={selected['area']:.0f}px, Score={selected['composite_score']:.4f}")
        print(f"    Best (by score): Area={best_by_score['area']:.0f}px, Score={best_by_score['composite_score']:.4f}")
        print(f"    The largest candidate is NOT the highest-scoring candidate!")


def main():
    print("\n" + "=" * 80)
    print("DEEP DIAGNOSTIC: SCORING AND CANDIDATE SELECTION")
    print("=" * 80)

    for bank_name, image_path in TEST_IMAGES.items():
        analyze_bank(bank_name, image_path)

    print("\n" + "=" * 80)
    print("END OF DIAGNOSIS")
    print("=" * 80)


if __name__ == "__main__":
    main()
