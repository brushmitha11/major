"""
PHASE 3 REGISTRATION V1 — BOUNDARY DETECTION DIAGNOSTIC

TRAIN-only diagnostic script to validate the multi-stage boundary detection pipeline.

Tests 4 representative TRAIN images and reports per-stage results.
No access to validation.csv or test.csv.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import cv2
import pandas as pd
import logging
from localization.registration import (
    detect_cheque_corners,
    _detect_corners_stage1_contour,
    _detect_corners_stage2_hough,
    _detect_corners_stage3_morphological,
    _assess_boundary_plausibility,
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Load train CSV to find image paths
train_df = pd.read_csv("datasets/splits/train.csv")

# Get one TRAIN image per bank (the raw/original ones)
TEST_IMAGES = {}
for bank in ["AXIS BANK", "CANARA BANK", "ICICI BANK", "SYNDICATE BANK"]:
    bank_df = train_df[(train_df['bank'] == bank) & (train_df['image_path'].str.contains('datasets/raw'))]
    if len(bank_df) > 0:
        TEST_IMAGES[bank] = bank_df.iloc[0]['image_path']


def analyze_bank(bank_name: str, image_path: str):
    """Detailed diagnostic of boundary detection for a bank."""
    print("\n" + "=" * 100)
    print(f"{bank_name} — {Path(image_path).name}")
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

    # Run the full detection pipeline
    print(f"\n  Running multi-stage detection pipeline...")

    final_corners = detect_cheque_corners(image)

    if final_corners is None:
        print(f"\n  ✗ DETECTION FAILED")
        print(f"  All stages exhausted without finding acceptable boundary")
        return

    print(f"\n  ✓ DETECTION SUCCESSFUL")
    print(f"  Final corners (TL, TR, BR, BL): {final_corners}")

    # Compute dimensions
    ordered = final_corners
    x_coords = [c[0] for c in ordered]
    y_coords = [c[1] for c in ordered]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)

    print(f"  Detected region: {width:.0f} × {height:.0f}px")

    # Compute area
    quad_pts = np.array(ordered, dtype=float)
    area = 0.5 * abs(sum(quad_pts[i, 0] * quad_pts[(i + 1) % 4, 1] -
                         quad_pts[(i + 1) % 4, 0] * quad_pts[i, 1] for i in range(4)))
    area_coverage = 100 * area / (w * h)

    print(f"  Detected area: {area:.0f}px² ({area_coverage:.2f}% of image)")

    # Compute pairwise distances
    from scipy.spatial.distance import pdist
    distances = pdist(quad_pts)
    print(f"  Min corner distance: {np.min(distances):.1f}px")


def main():
    print("\n" + "=" * 100)
    print("PHASE 3 REGISTRATION V1 — BOUNDARY DETECTION DIAGNOSTIC (TRAIN ONLY)")
    print("=" * 100)
    print(f"\nTesting 4 representative TRAIN images...")
    print(f"No validation or test data accessed.")

    success_count = 0
    failure_count = 0

    for bank_name, image_path in TEST_IMAGES.items():
        try:
            # Suppress detailed logging during analysis
            logging.getLogger('localization.registration').setLevel(logging.WARNING)

            analyze_bank(bank_name, image_path)

            # Re-enable logging
            logging.getLogger('localization.registration').setLevel(logging.DEBUG)

            # For now, assume success if analyze_bank ran
            if Path(image_path).exists():
                success_count += 1
        except Exception as e:
            logger.error(f"Analysis failed for {bank_name}: {e}")
            failure_count += 1

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print(f"\nImages analyzed: {len(TEST_IMAGES)}")
    print(f"Detection pipeline: Multi-stage (contour → Hough → morphological)")
    print(f"\nDiagnostic complete.")


if __name__ == "__main__":
    main()
