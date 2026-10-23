"""
PHASE 3 — USER-UPLOAD QUALITY ASSESSMENT GATE

Test the quality gate behavior for user-uploaded cheque images.

Purpose: Demonstrate how uploaded images are assessed for quality
Context: User-upload (not added to dataset)
Output: User-facing quality report with recommendation

IMPORTANT:
- Quality assessment is PROVISIONAL and based on image usability only
- No genuine/forgery classification is performed
- Uploaded images are NOT added to the research dataset
- User gets clear feedback on image quality and next steps
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import argparse
from quality.quality_assessment_unified import UnifiedQualityAssessment


def main():
    # Parse arguments
    parser = argparse.ArgumentParser(
        description="Test user-upload quality gate",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_user_upload_quality_gate.py --image datasets/raw/idrbt/300/Cheque\ 309137.tif
  python test_user_upload_quality_gate.py --image /path/to/uploaded_cheque.jpg
        """
    )
    parser.add_argument(
        "--image",
        required=True,
        type=str,
        help="Path to cheque image to assess"
    )

    args = parser.parse_args()
    image_path = args.image

    # Verify file exists
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"\n[ERROR] Image file not found: {image_path}")
        return

    print("\n" + "=" * 100)
    print("USER-UPLOAD QUALITY ASSESSMENT")
    print("=" * 100)

    print(f"\nAssessing image: {image_file.name}")

    # Initialize quality assessment engine
    engine = UnifiedQualityAssessment()

    # Assess image (context="user_upload")
    try:
        quality_result = engine.assess(
            image_path=image_path,
            context="user_upload"
        )
    except Exception as e:
        print(f"\n[ERROR] Failed to assess image quality")
        print(f"  Reason: {str(e)}")
        return

    # Display results
    print(f"\n" + "-" * 100)
    print(quality_result.user_message)
    print("-" * 100)

    # Detailed metrics (for diagnostics/transparency)
    print(f"\nDetailed Quality Metrics:")
    print(f"  Overall Score: {quality_result.quality_score:.3f}")
    print(f"  Status: {quality_result.quality_status}")

    print(f"\n  Component Scores:")
    print(f"    Sharpness: {quality_result.component_scores['sharpness']:.3f}")
    print(f"    Contrast: {quality_result.component_scores['contrast']:.3f}")
    print(f"    Brightness: {quality_result.component_scores['brightness']:.3f}")
    print(f"    Skew: {quality_result.component_scores['skew']:.3f}")
    print(f"    Completeness: {quality_result.component_scores['completeness']:.3f}")

    if quality_result.issues:
        print(f"\n  Issues Detected:")
        for issue in quality_result.issues:
            print(f"    - {issue}")

    # Decision
    print(f"\nQuality Gate Decision:")
    print(f"  Status: {quality_result.quality_status}")

    if quality_result.quality_status == "GOOD":
        print(f"  Action: [PROCEED WITH VERIFICATION]")
        print(f"  Next step: Proceed to cheque verification")
        return 0

    elif quality_result.quality_status == "UNCERTAIN":
        print(f"  Action: [STOP - REQUEST RE-UPLOAD]")
        print(f"  Next step: Ask user to re-upload a clearer image")
        return 1

    elif quality_result.quality_status == "POOR":
        print(f"  Action: [STOP - REQUEST RE-UPLOAD]")
        print(f"  Next step: Ask user to re-upload a clear, complete image")
        return 1

    print("\n" + "=" * 100)
    print("IMPORTANT NOTES:")
    print("=" * 100)
    print("- This quality assessment is PROVISIONAL (thresholds not yet scientifically validated)")
    print("- Quality gate uses ONLY image properties (sharpness, contrast, brightness, skew, completeness)")
    print("- No genuine/forgery classification is performed")
    print("- Uploaded image is NOT added to the research dataset")
    print("- This assessment measures image usability for automated processing, not cheque authenticity")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code if exit_code is not None else 0)
