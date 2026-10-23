"""
Deep diagnostic of _validate_quadrilateral_geometry() behavior.

Analyzes rejection reasons, threshold impacts, and candidate characteristics
for all convex 4-point candidates BEFORE geometry filtering.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
import pandas as pd
from localization.registration import _order_corners_deterministic

# Load train CSV to find image paths
train_df = pd.read_csv("datasets/splits/train.csv")

# Get one TRAIN image per bank (the raw/original ones)
TEST_IMAGES = {}
for bank in ["AXIS BANK", "CANARA BANK", "ICICI BANK", "SYNDICATE BANK"]:
    bank_df = train_df[(train_df['bank'] == bank) & (train_df['image_path'].str.contains('datasets/raw'))]
    if len(bank_df) > 0:
        TEST_IMAGES[bank] = bank_df.iloc[0]['image_path']


def compute_shoelace_area(quad_pts: np.ndarray) -> float:
    """Compute area using shoelace formula."""
    x, y = quad_pts[:, 0], quad_pts[:, 1]
    area = 0.5 * abs(sum(x[i] * y[(i + 1) % 4] - x[(i + 1) % 4] * y[i] for i in range(4)))
    return float(area)


def get_pairwise_distances(quad_pts: np.ndarray) -> np.ndarray:
    """Get all pairwise distances between 4 points."""
    distances = []
    for i in range(4):
        for j in range(i + 1, 4):
            dist = np.linalg.norm(quad_pts[i] - quad_pts[j])
            distances.append(dist)
    return np.array(distances)


def get_candidate_dims(quad_pts: np.ndarray) -> tuple:
    """Get width and height of candidate."""
    x_coords = quad_pts[:, 0]
    y_coords = quad_pts[:, 1]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)
    return width, height


def analyze_bank_geometry(bank_name: str, image_path: str):
    """Detailed geometry validation analysis for a bank."""
    print("\n" + "=" * 100)
    print(f"{bank_name} — {image_path}")
    print("=" * 100)

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

        contour_area = cv2.contourArea(contour)
        is_convex = cv2.isContourConvex(contour)
        all_4pt_candidates.append({
            'contour_idx': idx,
            'quad_pts': quad_pts,
            'contour_area': contour_area,
            'is_convex': is_convex,
            'contour': contour,
        })

    print(f"  Total 4-point candidates: {len(all_4pt_candidates)}")

    # Stage 2: After convexity filter
    convex_candidates = [c for c in all_4pt_candidates if c['is_convex']]
    print(f"  Convex 4-point candidates: {len(convex_candidates)}")

    if len(convex_candidates) == 0:
        print("\n  *** NO CONVEX CANDIDATES ***")
        return

    # ========== ANALYSIS 1: GEOMETRY METRICS FOR ALL CONVEX CANDIDATES ==========

    print(f"\n  === ANALYSIS 1: GEOMETRY METRICS (ALL {len(convex_candidates)} CONVEX CANDIDATES) ===")

    # Compute metrics for all convex candidates
    metrics = []
    for c in convex_candidates:
        quad_pts = c['quad_pts'].astype(float)

        # Areas
        shoelace = compute_shoelace_area(quad_pts)
        contour_area = c['contour_area']

        # Distances
        pairwise_distances = get_pairwise_distances(quad_pts)
        min_dist = np.min(pairwise_distances)
        max_dist = np.max(pairwise_distances)

        # Dimensions
        width, height = get_candidate_dims(quad_pts)

        metrics.append({
            'quad_pts': quad_pts,
            'contour_area': contour_area,
            'shoelace_area': shoelace,
            'min_pairwise_dist': min_dist,
            'max_pairwise_dist': max_dist,
            'width': width,
            'height': height,
            'pairwise_distances': pairwise_distances,
        })

    # Report statistics
    candidate_areas = [m['shoelace_area'] for m in metrics]
    min_distances = [m['min_pairwise_dist'] for m in metrics]

    print(f"\n  Candidate Area (shoelace):")
    print(f"    Min:    {np.min(candidate_areas):.1f} px²")
    print(f"    Max:    {np.max(candidate_areas):.1f} px²")
    print(f"    Median: {np.median(candidate_areas):.1f} px²")
    print(f"    95th %: {np.percentile(candidate_areas, 95):.1f} px²")

    print(f"\n  Minimum Pairwise Distance:")
    print(f"    Min:    {np.min(min_distances):.1f} px")
    print(f"    Max:    {np.max(min_distances):.1f} px")
    print(f"    Median: {np.median(min_distances):.1f} px")
    print(f"    95th %: {np.percentile(min_distances, 95):.1f} px")

    # ========== ANALYSIS 2: REJECTION REASONS ==========

    print(f"\n  === ANALYSIS 2: GEOMETRY REJECTION REASONS ===")

    rejection_counts = {'A': 0, 'B': 0, 'C': 0, 'D': 0}

    for m in metrics:
        quad_pts = m['quad_pts']
        shoelace = m['shoelace_area']
        min_dist = m['min_pairwise_dist']

        fails_separation = min_dist < 10
        fails_area = shoelace < 100

        if fails_separation and fails_area:
            rejection_counts['C'] += 1
        elif fails_separation:
            rejection_counts['A'] += 1
        elif fails_area:
            rejection_counts['B'] += 1
        else:
            rejection_counts['D'] += 1

    print(f"\n  Rejection breakdown ({len(convex_candidates)} convex candidates):")
    print(f"    A (min separation < 10):        {rejection_counts['A']}")
    print(f"    B (shoelace area < 100):        {rejection_counts['B']}")
    print(f"    C (both A and B):               {rejection_counts['C']}")
    print(f"    D (neither - PASSES BOTH):      {rejection_counts['D']}")
    print(f"    TOTAL REJECTED:                 {rejection_counts['A'] + rejection_counts['B'] + rejection_counts['C']}")
    print(f"    TOTAL PASSING:                  {rejection_counts['D']}")

    # ========== ANALYSIS 3: LARGEST CONVEX CANDIDATE ==========

    print(f"\n  === ANALYSIS 3: LARGEST CONVEX CANDIDATE BEFORE GEOMETRY FILTER ===")

    largest_idx = np.argmax([m['shoelace_area'] for m in metrics])
    largest = metrics[largest_idx]
    largest_convex = convex_candidates[largest_idx]

    quad_pts = largest['quad_pts']
    ordered = _order_corners_deterministic(quad_pts)

    print(f"\n  Raw points: {quad_pts.astype(int).tolist()}")
    if ordered:
        print(f"  Ordered (TL, TR, BR, BL): {ordered}")
    else:
        print(f"  Ordered: FAILED")

    print(f"\n  Metrics:")
    print(f"    Contour area:        {largest['contour_area']:.1f} px²")
    print(f"    Shoelace area:       {largest['shoelace_area']:.1f} px²")
    print(f"    Width × Height:      {largest['width']:.0f} × {largest['height']:.0f} px")
    print(f"    Min pairwise dist:   {largest['min_pairwise_dist']:.1f} px")
    print(f"    Max pairwise dist:   {largest['max_pairwise_dist']:.1f} px")

    print(f"\n  Geometry validation:")
    fails_sep = largest['min_pairwise_dist'] < 10
    fails_area = largest['shoelace_area'] < 100
    print(f"    Min separation < 10:     {fails_sep}")
    print(f"    Shoelace area < 100:     {fails_area}")
    print(f"    PASSES validation:       {not (fails_sep or fails_area)}")

    # ========== ANALYSIS 4: CONTOURAREA VS SHOELACE FOR TOP 10 CONVEX ==========

    print(f"\n  === ANALYSIS 4: CONTOURAREA VS SHOELACE (TOP 10 CONVEX BY AREA) ===")

    sorted_by_area = sorted(enumerate(metrics), key=lambda x: x[1]['shoelace_area'], reverse=True)

    print(f"\n  {'Rank':<5} {'Shoelace':<12} {'ContourArea':<12} {'Diff %':<10} {'Min Dist':<10} {'Status':<10}")
    print(f"  {'-'*70}")

    for rank, (idx, m) in enumerate(sorted_by_area[:10], 1):
        shoelace = m['shoelace_area']
        contour_area = m['contour_area']
        diff_pct = 100 * abs(shoelace - contour_area) / max(shoelace, contour_area)
        min_dist = m['min_pairwise_dist']

        fails_sep = min_dist < 10
        fails_area = shoelace < 100
        status = "PASS" if not (fails_sep or fails_area) else "REJECT"

        print(f"  {rank:<5} {shoelace:<12.1f} {contour_area:<12.1f} {diff_pct:<10.1f} {min_dist:<10.1f} {status:<10}")

    # ========== FINAL SUMMARY ==========

    print(f"\n  === ANALYSIS 5: SUMMARY STATS ===")

    passing_count = rejection_counts['D']
    total_convex = len(convex_candidates)
    rejection_pct = 100 * (total_convex - passing_count) / total_convex if total_convex > 0 else 0

    print(f"\n  Convex candidates:        {total_convex}")
    print(f"  Passing geometry:         {passing_count}")
    print(f"  Failing geometry:         {total_convex - passing_count}")
    print(f"  Failure rate:             {rejection_pct:.1f}%")

    if passing_count == 0:
        print(f"\n  *** 100% REJECTION - All convex candidates fail geometry validation ***")

        # Determine why
        if rejection_counts['C'] == total_convex:
            print(f"  Reason: ALL candidates fail BOTH checks (separation AND area)")
        elif rejection_counts['A'] == total_convex:
            print(f"  Reason: ALL candidates fail separation check (min dist < 10)")
        elif rejection_counts['B'] == total_convex:
            print(f"  Reason: ALL candidates fail area check (shoelace < 100)")
        else:
            print(f"  Reason: Mixed failures - A:{rejection_counts['A']}, B:{rejection_counts['B']}, C:{rejection_counts['C']}")


def main():
    print("\n" + "=" * 100)
    print("DEEP GEOMETRY VALIDATION DIAGNOSTIC")
    print("=" * 100)

    for bank_name, image_path in TEST_IMAGES.items():
        analyze_bank_geometry(bank_name, image_path)

    print("\n" + "=" * 100)
    print("END OF DIAGNOSTIC")
    print("=" * 100)


if __name__ == "__main__":
    main()
