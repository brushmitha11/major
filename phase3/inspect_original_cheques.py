#!/usr/bin/env python3
"""
Phase 3 Image Quality - Original Cheque Inspection
Visually inspect one reference cheque per bank to diagnose quality score differences
"""

import sys
from pathlib import Path
import pandas as pd
import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from preprocessing.image_loader import ImageLoader
from preprocessing.image_quality import ImageQualityAssessment


def inspect_originals():
    """Inspect original cheques per bank"""

    print("\n" + "="*80)
    print("PHASE 3 IMAGE QUALITY - ORIGINAL CHEQUE INSPECTION")
    print("="*80)

    # Load train split
    train_csv = Path("datasets/splits/train.csv")
    if not train_csv.exists():
        print(f"✗ Train CSV not found: {train_csv}")
        return

    train_df = pd.read_csv(train_csv)

    # Select one reference/original per bank
    banks = ['AXIS BANK', 'CANARA BANK', 'ICICI BANK', 'SYNDICATE BANK']

    # Filter for reference/original images (forgery_type == 'reference' or similar)
    original_images = []

    for bank in banks:
        # Get original/reference images for this bank
        bank_df = train_df[train_df['bank'] == bank]

        # Try to find 'reference' type, otherwise take first image
        ref_images = bank_df[bank_df['forgery_type'] == 'reference']

        if len(ref_images) > 0:
            original_images.append(ref_images.iloc[0])
        else:
            # Fallback: take first image
            original_images.append(bank_df.iloc[0])

    print(f"\nInspecting {len(original_images)} original cheques (1 per bank)\n")
    print("="*80)
    print("QUALITY ASSESSMENT + IMAGE ANALYSIS")
    print("="*80 + "\n")

    # Initialize tools
    loader = ImageLoader()
    quality_assessor = ImageQualityAssessment()

    for idx, row in enumerate(original_images, 1):
        image_path = row['image_path']
        bank = row['bank']
        forgery_type = row['forgery_type']

        print(f"\n[{idx}] {bank}")
        print(f"    File: {Path(image_path).name}")
        print(f"    Type: {forgery_type}")
        print(f"    Path: {image_path}")

        # Load image
        image = loader.load_image(image_path, verbose=False)
        if image is None:
            print(f"    ✗ Failed to load image")
            continue

        # Get image properties
        h, w, c = image.shape
        print(f"    Dimensions: {w}×{h} pixels, {c} channels")

        # Assess quality
        quality_result = quality_assessor.assess_image_quality(image)

        # Display component scores
        print(f"\n    Quality Component Scores:")
        print(f"      Sharpness:    {quality_result['sharpness']:.3f}")
        print(f"      Contrast:     {quality_result['contrast']:.3f}")
        print(f"      Brightness:   {quality_result['brightness']:.3f}")
        print(f"      Skew:         {quality_result['skew']:.3f}")
        print(f"      Completeness: {quality_result['completeness']:.3f}")
        print(f"    Combined Score: {quality_result['combined_score']:.3f}")
        print(f"    Gate Result: {'PASS' if quality_result['pass_quality_gate'] else 'FAIL'} (threshold: 0.65)")

        # Analyze brightness histogram
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

        very_dark = np.sum(gray < 30)
        very_bright = np.sum(gray > 240)
        mid_tone = np.sum((gray >= 30) & (gray <= 240))
        total = gray.size

        very_dark_ratio = very_dark / total
        very_bright_ratio = very_bright / total
        mid_tone_ratio = mid_tone / total

        mean_brightness = np.mean(gray)

        print(f"\n    Brightness Analysis:")
        print(f"      Mean grayscale: {mean_brightness:.1f}")
        print(f"      Very dark (<30): {very_dark_ratio*100:.1f}%")
        print(f"      Mid-tone (30-240): {mid_tone_ratio*100:.1f}%")
        print(f"      Very bright (>240): {very_bright_ratio*100:.1f}%")

        if very_bright_ratio > 0.99:
            print(f"      → Almost entirely white (severe overexposure?)")
        elif very_bright_ratio < 0.05:
            print(f"      → Very little white content (underexposed?)")
        elif very_dark_ratio > 0.80:
            print(f"      → Mostly dark content (negative/severe underexposure?)")
        elif very_dark_ratio < 0.01:
            print(f"      → Almost no dark text/borders (washed out?)")
        else:
            print(f"      → Normal document exposure")

        # Analyze edges for completeness
        edges = cv2.Canny(gray, 50, 150)
        edge_count = np.count_nonzero(edges)
        edge_density = edge_count / edges.size

        print(f"\n    Edge Analysis (Canny 50-150):")
        print(f"      Total edge pixels: {edge_count}")
        print(f"      Edge density: {edge_density*100:.2f}%")

        # Check borders
        border_width = int(0.1 * w)
        border_height = int(0.1 * h)

        top_edges = np.count_nonzero(edges[:border_height, :])
        bottom_edges = np.count_nonzero(edges[-border_height:, :])
        left_edges = np.count_nonzero(edges[:, :border_width])
        right_edges = np.count_nonzero(edges[:, -border_width:])

        print(f"      Border edge pixels:")
        print(f"        Top (10% of height): {top_edges}")
        print(f"        Bottom (10% of height): {bottom_edges}")
        print(f"        Left (10% of width): {left_edges}")
        print(f"        Right (10% of width): {right_edges}")

    print("\n" + "="*80)
    print("✅ INSPECTION COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    inspect_originals()
