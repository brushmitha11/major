#!/usr/bin/env python3
"""
Phase 3 Image Quality - Broader Diagnostic by Bank
Tests 3 representative images per bank to investigate completeness scores
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from preprocessing.image_loader import ImageLoader
from preprocessing.image_quality import ImageQualityAssessment


def run_diagnostic():
    """Run quality assessment on 3 images per bank"""

    print("\n" + "="*80)
    print("PHASE 3 IMAGE QUALITY - BROADER DIAGNOSTIC BY BANK")
    print("="*80)

    # Load train split
    train_csv = Path("datasets/splits/train.csv")
    if not train_csv.exists():
        print(f"✗ Train CSV not found: {train_csv}")
        return

    train_df = pd.read_csv(train_csv)
    print(f"\nTrain split loaded: {len(train_df)} images\n")

    # Select 3 images per bank
    banks = ['AXIS BANK', 'CANARA BANK', 'ICICI BANK', 'SYNDICATE BANK']
    samples = []

    for bank in banks:
        bank_images = train_df[train_df['bank'] == bank].head(3)
        samples.extend(bank_images.to_dict('records'))

    print(f"Testing on {len(samples)} representative samples (3 per bank)\n")
    print("="*80)
    print("DETAILED RESULTS")
    print("="*80 + "\n")

    # Initialize tools
    loader = ImageLoader()
    quality_assessor = ImageQualityAssessment()

    results = []

    for idx, row in enumerate(samples, 1):
        image_path = row['image_path']
        bank = row['bank']
        forgery_type = row['forgery_type']

        print(f"[{idx}] {Path(image_path).name}")
        print(f"    Bank: {bank} | Type: {forgery_type}")

        # Load image
        image = loader.load_image(image_path, verbose=False)
        if image is None:
            print(f"    ✗ Failed to load image")
            continue

        # Assess quality
        quality_result = quality_assessor.assess_image_quality(image)

        # Display component scores
        print(f"    Scores: Sharp={quality_result['sharpness']:.3f}, "
              f"Contrast={quality_result['contrast']:.3f}, "
              f"Bright={quality_result['brightness']:.3f}, "
              f"Skew={quality_result['skew']:.3f}, "
              f"Complete={quality_result['completeness']:.3f}")
        print(f"    Combined: {quality_result['combined_score']:.3f}\n")

        results.append({
            'bank': bank,
            'forgery_type': forgery_type,
            'sharpness': quality_result['sharpness'],
            'contrast': quality_result['contrast'],
            'brightness': quality_result['brightness'],
            'skew': quality_result['skew'],
            'completeness': quality_result['completeness'],
            'combined_score': quality_result['combined_score']
        })

    # Analysis by bank
    print("="*80)
    print("SUMMARY BY BANK")
    print("="*80 + "\n")

    for bank in banks:
        bank_results = [r for r in results if r['bank'] == bank]

        if not bank_results:
            continue

        print(f"{bank}:")
        print(f"  Samples: {len(bank_results)}")

        # Component statistics
        components = ['sharpness', 'contrast', 'brightness', 'skew', 'completeness', 'combined_score']

        for component in components:
            values = [r[component] for r in bank_results]
            mean_val = np.mean(values)
            min_val = np.min(values)
            max_val = np.max(values)

            print(f"    {component:15s}: min={min_val:.3f}, max={max_val:.3f}, mean={mean_val:.3f}")

        print()

    # Overall statistics
    print("="*80)
    print("OVERALL STATISTICS (ALL 12 SAMPLES)")
    print("="*80 + "\n")

    for component in components:
        values = [r[component] for r in results]
        mean_val = np.mean(values)
        min_val = np.min(values)
        max_val = np.max(values)

        print(f"{component:15s}: min={min_val:.3f}, max={max_val:.3f}, mean={mean_val:.3f}")

    print("\n" + "="*80)
    print("✅ DIAGNOSTIC COMPLETE")
    print("="*80 + "\n")

    return results


if __name__ == "__main__":
    run_diagnostic()
