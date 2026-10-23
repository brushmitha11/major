#!/usr/bin/env python3
"""
Phase 3 Field Localization V1 — Sanity Test

Integration test of template-based field localization pipeline using 4 representative
TRAIN-split images (1 per bank).

Purpose: Verify end-to-end localization works; report registration and field-extraction results.
Do NOT interpret as performance metrics; no thresholds tuned.

Data Protection: TRAIN split only. No validation.csv or test.csv access.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from preprocessing.image_loader import ImageLoader
from localization.field_localization import FieldLocalizationV1


def run_sanity_test():
    """Run localization on 4 representative TRAIN images (1 per bank)"""

    print("\n" + "="*80)
    print("PHASE 3 FIELD LOCALIZATION V1 — SANITY TEST")
    print("="*80 + "\n")

    # Load train split only (no validation.csv or test.csv)
    train_csv = Path("datasets/splits/train.csv")
    if not train_csv.exists():
        print(f"✗ Train CSV not found: {train_csv}")
        return

    train_df = pd.read_csv(train_csv)
    print(f"Train split loaded: {len(train_df)} images\n")

    # Define 4 representative TRAIN images (1 per bank)
    test_images = [
        ('AXIS BANK', 'Cheque 309137.tif'),
        ('CANARA BANK', 'Cheque 120612.tif'),
        ('ICICI BANK', 'Cheque 100829.tif'),
        ('SYNDICATE BANK', 'Cheque 083657.tif'),
    ]

    print(f"Testing on {len(test_images)} representative TRAIN samples (1 per bank)\n")
    print("="*80)
    print("DETAILED LOCALIZATION RESULTS")
    print("="*80 + "\n")

    # Initialize tools
    loader = ImageLoader()
    localizer = FieldLocalizationV1()

    results = []

    for idx, (bank, filename) in enumerate(test_images, 1):
        print(f"\n[{idx}] {filename}")
        print(f"    Bank: {bank}")

        # Find image in train split
        matching_rows = train_df[
            (train_df['bank'] == bank) &
            (train_df['image_path'].str.contains(filename, na=False))
        ]

        if len(matching_rows) == 0:
            print(f"    ✗ Image not found in TRAIN split")
            continue

        image_path = matching_rows.iloc[0]['image_path']
        print(f"    Path: {image_path}")

        # Load image
        image = loader.load_image(image_path, verbose=False)
        if image is None:
            print(f"    ✗ Failed to load image")
            continue

        print(f"    Image shape: {image.shape}")

        # Run localization
        loc_result = localizer.localize_fields(image, bank, quality_score=None)

        # Display registration results
        print(f"\n    Registration:")
        print(f"      Success: {loc_result.registration_success}")
        print(f"      Confidence: {loc_result.registration_confidence:.3f} (diagnostic measure)")
        if loc_result.registration_residual is not None:
            print(f"      Residual (RMSE): {loc_result.registration_residual:.2f} pixels")
        if loc_result.detected_corners:
            print(f"      Detected corners (TL, TR, BR, BL):")
            for i, corner in enumerate(loc_result.detected_corners):
                corner_names = ['TL', 'TR', 'BR', 'BL']
                print(f"        {corner_names[i]}: {corner}")

        if loc_result.transform_params:
            print(f"      Transform params:")
            print(f"        Scale: sx={loc_result.transform_params.get('sx', 'N/A'):.3f}, "
                  f"sy={loc_result.transform_params.get('sy', 'N/A'):.3f}")
            print(f"        Rotation: {loc_result.transform_params.get('rotation_deg', 'N/A'):.1f}°")

        # Display field results
        print(f"\n    Fields ({len(loc_result.applicable_fields)} applicable):")
        for field_name in loc_result.applicable_fields:
            crop_result = loc_result.fields.get(field_name)
            if crop_result:
                status = "✓ VALID" if crop_result.is_valid else "✗ INVALID"
                print(f"      {field_name}: {status}")
                if crop_result.is_valid:
                    print(f"        Crop shape: {crop_result.crop.shape if crop_result.crop is not None else 'None'}")
                    print(f"        Original bbox: {crop_result.bbox_original}")
                    print(f"        Transformed bbox: {crop_result.bbox_transformed}")
                else:
                    print(f"        Reason: {crop_result.reason}")

        # Overall status
        print(f"\n    Overall Status: {loc_result.status}")
        print(f"    Successful fields: {loc_result.successful_fields}/{loc_result.total_fields}")
        if loc_result.failure_reason:
            print(f"    Failure reason: {loc_result.failure_reason}")

        results.append({
            'bank': bank,
            'filename': filename,
            'image_shape': image.shape,
            'registration_success': loc_result.registration_success,
            'registration_confidence': loc_result.registration_confidence,
            'registration_residual': loc_result.registration_residual,
            'status': loc_result.status,
            'successful_fields': loc_result.successful_fields,
            'total_fields': loc_result.total_fields
        })

    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80 + "\n")

    if results:
        print(f"Total samples tested: {len(results)}")
        print(f"\nBank-wise results:")
        for r in results:
            print(f"  {r['bank']:20s}: {r['status']:20s} "
                  f"(confidence={r['registration_confidence']:.3f}, "
                  f"fields={r['successful_fields']}/{r['total_fields']})")

        # Aggregate statistics
        print(f"\nRegistration statistics:")
        successes = sum(1 for r in results if r['registration_success'])
        print(f"  Successful registrations: {successes}/{len(results)}")

        confidences = [r['registration_confidence'] for r in results]
        print(f"  Confidence range: [{min(confidences):.3f}, {max(confidences):.3f}]")
        print(f"  Mean confidence: {np.mean(confidences):.3f}")

        residuals = [r['registration_residual'] for r in results if r['registration_residual'] is not None]
        if residuals:
            print(f"  Residual range: [{min(residuals):.2f}, {max(residuals):.2f}] pixels")
            print(f"  Mean residual: {np.mean(residuals):.2f} pixels")

        field_success = sum(r['successful_fields'] for r in results)
        total_fields = sum(r['total_fields'] for r in results)
        print(f"\nField extraction:")
        print(f"  Total fields: {total_fields}")
        print(f"  Successfully extracted: {field_success}/{total_fields}")

        status_counts = {}
        for r in results:
            status = r['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        print(f"\nStatus distribution:")
        for status, count in sorted(status_counts.items()):
            print(f"  {status}: {count}")

    print("\n" + "="*80)
    print("✅ SANITY TEST COMPLETE")
    print("="*80 + "\n")

    return results


if __name__ == "__main__":
    run_sanity_test()
