#!/usr/bin/env python3
"""
Diagnostic: Corner Detection Analysis

Investigate why corner detection is selecting small internal quadrilaterals
instead of the full cheque document boundary.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import cv2

sys.path.insert(0, str(Path(__file__).parent))

from preprocessing.image_loader import ImageLoader
from localization.registration import detect_cheque_corners


def diagnose_corner_detection():
    """Diagnose corner detection failures"""

    print("\n" + "="*80)
    print("DIAGNOSTIC: CORNER DETECTION ANALYSIS")
    print("="*80 + "\n")

    # Load train split
    train_csv = Path("datasets/splits/train.csv")
    train_df = pd.read_csv(train_csv)

    test_images = [
        ('AXIS BANK', 'Cheque 309137.tif'),
        ('CANARA BANK', 'Cheque 120612.tif'),
        ('ICICI BANK', 'Cheque 100829.tif'),
        ('SYNDICATE BANK', 'Cheque 083657.tif'),
    ]

    loader = ImageLoader()

    for bank, filename in test_images:
        print(f"\n{bank} — {filename}")
        print("-" * 80)

        # Find and load image
        matching_rows = train_df[
            (train_df['bank'] == bank) &
            (train_df['image_path'].str.contains(filename, na=False))
        ]

        if len(matching_rows) == 0:
            print("  Image not found in TRAIN split")
            continue

        image_path = matching_rows.iloc[0]['image_path']
        image = loader.load_image(image_path, verbose=False)
        if image is None:
            print("  Failed to load image")
            continue

        h, w = image.shape[:2]
        print(f"  Image dimensions: {w} × {h}")

        # Detect edges
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        edge_count = np.count_nonzero(edges)
        print(f"  Edge pixels detected: {edge_count} ({100*edge_count/(w*h):.2f}% of image)")

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        print(f"  Total contours found: {len(contours)}")

        # Analyze all quadrilateral candidates
        quad_candidates = []
        for i, contour in enumerate(contours):
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)

            if len(approx) == 4:
                quad_pts = approx.squeeze().astype(int)
                if quad_pts.ndim == 1:
                    quad_pts = quad_pts.reshape(1, -1)

                if quad_pts.shape[0] == 4:
                    area = cv2.contourArea(contour)
                    is_convex = cv2.isContourConvex(contour)

                    # Calculate bounds
                    x_coords = quad_pts[:, 0]
                    y_coords = quad_pts[:, 1]
                    bounds_w = max(x_coords) - min(x_coords)
                    bounds_h = max(y_coords) - min(y_coords)

                    quad_candidates.append({
                        'index': i,
                        'area': area,
                        'convex': is_convex,
                        'bounds_w': bounds_w,
                        'bounds_h': bounds_h,
                        'points': quad_pts,
                    })

        print(f"\n  Quadrilateral candidates: {len(quad_candidates)}")

        # Sort by area descending
        quad_candidates.sort(key=lambda x: x['area'], reverse=True)

        # Show top 5 candidates
        print(f"\n  Top 5 candidates by area:")
        for i, cand in enumerate(quad_candidates[:5]):
            print(f"    [{i+1}] Area={cand['area']:.0f}px, "
                  f"Convex={cand['convex']}, "
                  f"Bounds={cand['bounds_w']}×{cand['bounds_h']}px")
            print(f"         Points: {cand['points'].tolist()}")

        # Run actual corner detection
        detected = detect_cheque_corners(image)
        print(f"\n  Detected corners by detect_cheque_corners():")
        if detected:
            for i, corner in enumerate(['TL', 'TR', 'BR', 'BL']):
                print(f"    {corner}: {detected[i]}")

            # Calculate size of detected corners
            x_coords = [c[0] for c in detected]
            y_coords = [c[1] for c in detected]
            det_w = max(x_coords) - min(x_coords)
            det_h = max(y_coords) - min(y_coords)
            print(f"  Detected region: {det_w}×{det_h}px "
                  f"({100*det_w/w:.1f}% width, {100*det_h/h:.1f}% height)")
        else:
            print("    FAILED - no valid quadrilateral found")

        print()


if __name__ == "__main__":
    diagnose_corner_detection()
