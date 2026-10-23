"""
Batch analyze image quality for all images in the dataset.
Generates a comprehensive quality report with statistics.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import cv2
import json
from collections import defaultdict
from datetime import datetime
from quality.quality_assessment_unified import UnifiedQualityAssessment
import pandas as pd

def analyze_dataset_quality():
    """Analyze quality of all images in dataset directories."""

    quality_engine = UnifiedQualityAssessment()
    results = []
    dataset_root = Path(__file__).parent.parent / "datasets"

    print("🔍 Starting Dataset Quality Analysis...")
    print(f"📁 Dataset root: {dataset_root}")
    print("-" * 80)

    # Find all image files
    image_extensions = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
    image_files = []

    for ext in image_extensions:
        image_files.extend(dataset_root.glob(f"**/*{ext}"))
        image_files.extend(dataset_root.glob(f"**/*{ext.upper()}"))

    if not image_files:
        print(f"⚠️  No images found in {dataset_root}")
        return

    print(f"📊 Found {len(image_files)} image(s) to analyze\n")

    # Analyze each image
    for idx, image_path in enumerate(image_files, 1):
        try:
            print(f"[{idx}/{len(image_files)}] Analyzing: {image_path.name}")

            # Read image
            image = cv2.imread(str(image_path))
            if image is None:
                print(f"  ❌ Could not read image")
                continue

            # Convert BGR to RGB
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            # Assess quality
            quality_result = quality_engine.assess(
                image_array=image,
                context="dataset_analysis"
            )

            result = {
                "file_name": image_path.name,
                "file_path": str(image_path.relative_to(dataset_root)),
                "quality_score": round(quality_result.quality_score, 3),
                "quality_status": quality_result.quality_status,
                "sharpness": round(quality_result.component_scores["sharpness"], 3),
                "contrast": round(quality_result.component_scores["contrast"], 3),
                "brightness": round(quality_result.component_scores["brightness"], 3),
                "skew": round(quality_result.component_scores["skew"], 3),
                "completeness": round(quality_result.component_scores["completeness"], 3),
                "issues": quality_result.issues,
                "recommendation": quality_result.recommendation,
            }

            results.append(result)

            # Print summary
            print(f"  ✓ Score: {result['quality_score']:.1%} | Status: {result['quality_status']}")
            if result['issues']:
                for issue in result['issues']:
                    print(f"    ⚠️  {issue}")

        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            continue

    if not results:
        print("❌ No images were successfully analyzed")
        return

    # Generate statistics
    print("\n" + "=" * 80)
    print("📈 DATASET QUALITY STATISTICS")
    print("=" * 80)

    df = pd.DataFrame(results)

    print(f"\nTotal images analyzed: {len(results)}")
    print(f"\nQuality Status Distribution:")
    status_counts = df['quality_status'].value_counts()
    for status, count in status_counts.items():
        percentage = (count / len(results)) * 100
        print(f"  {status}: {count} images ({percentage:.1f}%)")

    print(f"\nQuality Score Statistics:")
    print(f"  Average: {df['quality_score'].mean():.3f} ({df['quality_score'].mean()*100:.1f}%)")
    print(f"  Min: {df['quality_score'].min():.3f} ({df['quality_score'].min()*100:.1f}%)")
    print(f"  Max: {df['quality_score'].max():.3f} ({df['quality_score'].max()*100:.1f}%)")
    print(f"  Median: {df['quality_score'].median():.3f} ({df['quality_score'].median()*100:.1f}%)")

    print(f"\nComponent Average Scores:")
    components = ['sharpness', 'contrast', 'brightness', 'skew', 'completeness']
    for comp in components:
        avg = df[comp].mean()
        print(f"  {comp.capitalize()}: {avg:.3f} ({avg*100:.1f}%)")

    print(f"\nCommon Issues:")
    all_issues = []
    for issues_list in df['issues']:
        all_issues.extend(issues_list)

    if all_issues:
        issue_counts = defaultdict(int)
        for issue in all_issues:
            issue_counts[issue] += 1

        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(results)) * 100
            print(f"  {issue}: {count} images ({percentage:.1f}%)")
    else:
        print("  No issues detected!")

    # Save detailed report
    report_path = Path(__file__).parent / "dataset_quality_report.json"
    with open(report_path, 'w') as f:
        json.dump({
            "analysis_timestamp": datetime.now().isoformat(),
            "total_images": len(results),
            "status_distribution": status_counts.to_dict(),
            "quality_statistics": {
                "mean": float(df['quality_score'].mean()),
                "min": float(df['quality_score'].min()),
                "max": float(df['quality_score'].max()),
                "median": float(df['quality_score'].median()),
                "std": float(df['quality_score'].std()),
            },
            "component_averages": {comp: float(df[comp].mean()) for comp in components},
            "issue_counts": dict(sorted(
                [(k, int(v)) for k, v in issue_counts.items()],
                key=lambda x: x[1],
                reverse=True
            )),
            "detailed_results": results,
        }, f, indent=2)

    print(f"\n✅ Detailed report saved to: {report_path}")

    # Save CSV for easy viewing
    csv_path = Path(__file__).parent / "dataset_quality_report.csv"
    df.to_csv(csv_path, index=False)
    print(f"✅ CSV report saved to: {csv_path}")

    # Print top 5 best and worst images
    print("\n" + "=" * 80)
    print("🌟 TOP 5 BEST QUALITY IMAGES")
    print("=" * 80)
    best = df.nlargest(5, 'quality_score')[['file_name', 'quality_score', 'quality_status']]
    for idx, row in best.iterrows():
        print(f"  {row['file_name']}: {row['quality_score']:.1%} ({row['quality_status']})")

    print("\n" + "=" * 80)
    print("⚠️  BOTTOM 5 WORST QUALITY IMAGES")
    print("=" * 80)
    worst = df.nsmallest(5, 'quality_score')[['file_name', 'quality_score', 'quality_status']]
    for idx, row in worst.iterrows():
        print(f"  {row['file_name']}: {row['quality_score']:.1%} ({row['quality_status']})")

    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("=" * 80)

if __name__ == "__main__":
    analyze_dataset_quality()
