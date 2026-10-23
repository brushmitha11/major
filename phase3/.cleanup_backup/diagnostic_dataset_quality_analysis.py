"""
PHASE 3 — DATASET IMAGE QUALITY ANALYSIS

Analyze all 315 TRAIN images for quality assessment.

Purpose: Research analysis of dataset image quality
Context: TRAIN-only, no validation/test access
Output: CSV report + summary statistics
Expected: Exactly 315 TRAIN images analyzed, 0 failures

IMPORTANT: The quality thresholds are PROVISIONAL and NOT scientifically validated.
Quality scoring uses ONLY image properties, never label or forgery_type.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from quality.quality_assessment_unified import UnifiedQualityAssessment


def main():
    print("\n" + "=" * 100)
    print("PHASE 3 — DATASET IMAGE QUALITY ANALYSIS (TRAIN ONLY)")
    print("=" * 100)

    # Load TRAIN split
    print("\nLoading TRAIN split...")
    train_df = pd.read_csv("datasets/splits/train.csv")

    train_images = train_df[['image_path', 'parent_id', 'bank', 'label', 'forgery_type']].copy()
    expected_count = 315
    actual_count = len(train_images)

    print(f"[OK] Loaded {actual_count} images")

    # Verify exact count
    if actual_count != expected_count:
        print(f"\n[ERROR] Expected {expected_count} TRAIN images, got {actual_count}")
        print("  Analysis aborted. Dataset may have been modified.")
        return

    print(f"[OK] Verified: {actual_count} TRAIN images (expected {expected_count})")
    print(f"  Banks: {', '.join(sorted(train_images['bank'].unique()))}")

    # Initialize quality assessment engine
    engine = UnifiedQualityAssessment()

    # Analyze all images
    print(f"\nAnalyzing {actual_count} TRAIN images...")
    print("(This may take 3-5 minutes)")

    results = []
    failed_images = []

    for idx, (_, row) in enumerate(train_images.iterrows()):
        image_path = row['image_path']

        try:
            # Assess quality (context="dataset", no genuine/forgery claims)
            quality_result = engine.assess(
                image_path=image_path,
                context="dataset"
            )

            # Record result (including metadata for traceability, but not used in scoring)
            result_dict = quality_result.to_dict()
            result_dict.update({
                'image_path': image_path,
                'parent_id': row['parent_id'],
                'bank': row['bank'],
                'label': row['label'],
                'forgery_type': row['forgery_type'],
            })

            results.append(result_dict)

            # Progress indicator
            if (idx + 1) % 50 == 0:
                print(f"  Processed {idx + 1}/{actual_count}")

        except Exception as e:
            failed_images.append({
                'image_path': image_path,
                'error': str(e)
            })
            print(f"  [WARN] Failed to process: {image_path}")

    # Verify analysis completion
    print(f"\nAnalysis complete")

    if len(failed_images) > 0:
        print(f"\n[ERROR] {len(failed_images)}/{actual_count} images failed to process")
        for item in failed_images[:10]:
            print(f"  - {item['image_path']}: {item['error']}")
        print("\nAnalysis aborted. Not all TRAIN images could be analyzed.")
        return

    if len(results) != expected_count:
        print(f"\n[ERROR] Expected {expected_count} results, got {len(results)}")
        print("Analysis aborted.")
        return

    print(f"[OK] Successfully analyzed {len(results)}/{expected_count} TRAIN images")

    # Convert to DataFrame
    results_df = pd.DataFrame(results)

    # Safety: Verify no empty results
    if len(results_df) == 0:
        print("\n[ERROR] No results to analyze (empty DataFrame)")
        return

    # Save CSV report
    report_path = "phase3/dataset_quality_report.csv"
    results_df.to_csv(report_path, index=False)
    print(f"[OK] CSV report saved: {report_path}")

    # Generate summary statistics
    print("\n" + "=" * 100)
    print("SUMMARY STATISTICS")
    print("=" * 100)

    print(f"\nOverall Quality Distribution:")
    quality_dist = results_df['quality_status'].value_counts().sort_index()
    for status in ['GOOD', 'UNCERTAIN', 'POOR']:
        count = quality_dist.get(status, 0)
        pct = 100 * count / len(results_df)
        print(f"  {status}: {count} images ({pct:.1f}%)")

    print(f"\nQuality by Bank:")
    for bank in sorted(results_df['bank'].unique()):
        bank_data = results_df[results_df['bank'] == bank]
        good = len(bank_data[bank_data['quality_status'] == 'GOOD'])
        uncertain = len(bank_data[bank_data['quality_status'] == 'UNCERTAIN'])
        poor = len(bank_data[bank_data['quality_status'] == 'POOR'])

        print(f"\n  {bank} ({len(bank_data)} images):")
        print(f"    GOOD: {good} ({100*good/len(bank_data):.1f}%)")
        print(f"    UNCERTAIN: {uncertain} ({100*uncertain/len(bank_data):.1f}%)")
        print(f"    POOR: {poor} ({100*poor/len(bank_data):.1f}%)")
        print(f"    Avg quality score: {bank_data['quality_score'].mean():.3f}")

    print(f"\nComponent Averages (all TRAIN images):")
    print(f"  Sharpness: {results_df['sharpness'].mean():.3f}")
    print(f"  Contrast: {results_df['contrast'].mean():.3f}")
    print(f"  Brightness: {results_df['brightness'].mean():.3f}")
    print(f"  Skew: {results_df['skew'].mean():.3f}")
    print(f"  Completeness: {results_df['completeness'].mean():.3f}")

    print(f"\nQuality Score Range:")
    print(f"  Highest: {results_df['quality_score'].max():.3f}")
    print(f"  Lowest: {results_df['quality_score'].min():.3f}")
    print(f"  Mean: {results_df['quality_score'].mean():.3f}")
    print(f"  Median: {results_df['quality_score'].median():.3f}")

    # Representative examples per bank (closest to median quality_score)
    print(f"\nRepresentative Examples by Bank (closest to median quality_score):")
    for bank in sorted(results_df['bank'].unique()):
        bank_data = results_df[results_df['bank'] == bank]
        median_score = bank_data['quality_score'].median()

        # Find image closest to median
        closest_idx = (bank_data['quality_score'] - median_score).abs().idxmin()
        example = results_df.loc[closest_idx]

        print(f"\n  {bank}:")
        print(f"    Image: {Path(example['image_path']).name}")
        print(f"    Quality Score: {example['quality_score']:.3f}")
        print(f"    Status: {example['quality_status']}")
        print(f"    Sharpness: {example['sharpness']:.3f}")
        print(f"    Contrast: {example['contrast']:.3f}")
        print(f"    Brightness: {example['brightness']:.3f}")
        print(f"    Skew: {example['skew']:.3f}")
        print(f"    Completeness: {example['completeness']:.3f}")
        if example['issues']:
            print(f"    Issues: {example['issues']}")

    print(f"\nTop 5 Highest Quality Images (all banks):")
    top_5 = results_df.nlargest(5, 'quality_score')[['image_path', 'bank', 'quality_score', 'quality_status']]
    for idx, (_, row) in enumerate(top_5.iterrows(), 1):
        print(f"  {idx}. {row['bank']}: {row['quality_score']:.3f} ({row['quality_status']}) — {Path(row['image_path']).name}")

    print(f"\nTop 5 Lowest Quality Images (all banks):")
    bottom_5 = results_df.nsmallest(5, 'quality_score')[['image_path', 'bank', 'quality_score', 'quality_status']]
    for idx, (_, row) in enumerate(bottom_5.iterrows(), 1):
        print(f"  {idx}. {row['bank']}: {row['quality_score']:.3f} ({row['quality_status']}) — {Path(row['image_path']).name}")

    print("\n" + "=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)
    print(f"\nReport saved to: {report_path}")
    print(f"Total images analyzed: {len(results)}/{expected_count}")

    print("\nIMPORTANT NOTES:")
    print("- Quality thresholds (0.65/0.50) are PROVISIONAL and NOT scientifically validated")
    print("- Quality scoring uses ONLY image properties (sharpness, contrast, brightness, skew, completeness)")
    print("- Label and forgery_type are included for traceability but NOT used in quality determination")
    print("- This analysis is for research purposes only")
    print("- Dataset images and CSV files have NOT been modified")
    print("- No genuine/forgery claims are made based on image quality")


if __name__ == "__main__":
    main()
