#!/usr/bin/env python3
"""
Phase 3 Image Quality Module - Sanity Test
Test quality assessment on a small sample of representative cheque images
"""

import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

from preprocessing.image_loader import ImageLoader
from preprocessing.image_quality import ImageQualityAssessment

def test_image_quality():
    """Test quality assessment on a small sample of cheque images"""

    print("\n" + "="*70)
    print("PHASE 3 IMAGE QUALITY MODULE - SANITY TEST")
    print("="*70)

    # Load train split
    train_csv = Path("datasets/splits/train.csv")
    if not train_csv.exists():
        print(f"✗ Train CSV not found: {train_csv}")
        return

    train_df = pd.read_csv(train_csv)
    print(f"\nTrain split loaded: {len(train_df)} images")

    # Select 5 representative samples (one from each group)
    # 1. Reference image
    # 2. Amount forgery
    # 3. Payee forgery
    # 4. Multi-field forgery
    # 5. Date forgery (if available)

    sample_types = [
        ('reference', 1),
        ('amount_forgery', 1),
        ('payee_forgery', 1),
        ('multi_field_forgery', 1),
        ('date_forgery', 1)
    ]

    samples = []
    for forgery_type, count in sample_types:
        matching = train_df[train_df['forgery_type'] == forgery_type].head(count)
        samples.extend(matching.to_dict('records'))

    print(f"Testing on {len(samples)} representative samples")
    print("\n" + "="*70)
    print("QUALITY ASSESSMENT RESULTS")
    print("="*70)

    # Initialize tools
    loader = ImageLoader()
    quality_assessor = ImageQualityAssessment()

    results = []

    for idx, row in enumerate(samples, 1):
        image_path = row['image_path']
        forgery_type = row['forgery_type']
        bank = row['bank']

        print(f"\n[{idx}] {Path(image_path).name}")
        print(f"    Type: {forgery_type} | Bank: {bank}")

        # Load image
        image = loader.load_image(image_path, verbose=False)
        if image is None:
            print(f"    ✗ Failed to load image")
            continue

        # Preprocess for MobileNetV2 (get preprocessed image, but also need raw for quality)
        # For quality assessment, we need the raw RGB image
        if image.shape[-1] != 3:
            print(f"    ✗ Image not RGB (shape: {image.shape})")
            continue

        # Assess quality
        quality_result = quality_assessor.assess_image_quality(image)

        # Display component scores
        print(f"    Component Scores:")
        print(f"      Sharpness:    {quality_result['sharpness']:.3f}")
        print(f"      Contrast:     {quality_result['contrast']:.3f}")
        print(f"      Brightness:   {quality_result['brightness']:.3f}")
        print(f"      Skew:         {quality_result['skew']:.3f}")
        print(f"      Completeness: {quality_result['completeness']:.3f}")

        print(f"    Combined Score: {quality_result['combined_score']:.3f}")

        # Check quality gate
        pass_status = "✓ PASS" if quality_result['pass_quality_gate'] else "✗ FAIL"
        threshold = quality_result['threshold_used']
        print(f"    Quality Gate: {pass_status} (threshold: {threshold})")

        results.append({
            'filename': Path(image_path).name,
            'type': forgery_type,
            'bank': bank,
            'sharpness': quality_result['sharpness'],
            'contrast': quality_result['contrast'],
            'brightness': quality_result['brightness'],
            'skew': quality_result['skew'],
            'completeness': quality_result['completeness'],
            'combined_score': quality_result['combined_score'],
            'passes_gate': quality_result['pass_quality_gate']
        })

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)

    if results:
        pass_count = sum(1 for r in results if r['passes_gate'])
        fail_count = len(results) - pass_count

        print(f"\nTotal samples tested: {len(results)}")
        print(f"Passed quality gate (>= 0.65): {pass_count}/{len(results)}")
        print(f"Failed quality gate (< 0.65): {fail_count}/{len(results)}")

        print(f"\nScore ranges:")
        combined_scores = [r['combined_score'] for r in results]
        print(f"  Min: {min(combined_scores):.3f}")
        print(f"  Max: {max(combined_scores):.3f}")
        print(f"  Mean: {sum(combined_scores)/len(combined_scores):.3f}")

        print(f"\nComponent score ranges:")
        for component in ['sharpness', 'contrast', 'brightness', 'skew', 'completeness']:
            values = [r[component] for r in results]
            print(f"  {component:15s}: [{min(values):.3f}, {max(values):.3f}]")

    print("\n" + "="*70)
    print("✅ SANITY TEST COMPLETE")
    print("="*70 + "\n")

    return results

if __name__ == "__main__":
    test_image_quality()
