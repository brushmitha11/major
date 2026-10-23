#!/usr/bin/env python
"""
IDRBT Dataset Validation Script
Verifies dataset integrity and completeness
"""

import os
import sys
import pandas as pd
import hashlib
from pathlib import Path
from PIL import Image
from collections import Counter

def get_file_hash(filepath):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        return None

def validate_dataset():
    """Run complete validation"""
    print("=" * 70)
    print("IDRBT DATASET VALIDATION REPORT")
    print("=" * 70)

    # Paths
    images_dir = Path('datasets/raw/idrbt/300')
    manifest_path = Path('datasets/metadata/idrbt_manifest.csv')
    original_images_dir = Path('IDRBT_Cheque_Image_Dataset (1)/IDRBT Cheque Image Dataset/300')

    errors = []
    warnings = []

    # 1. Check image count
    print("\n1. IMAGE COUNT VERIFICATION")
    print("-" * 70)
    image_files = list(images_dir.glob('*.tif'))
    actual_count = len(image_files)
    print(f"Expected: 112 images")
    print(f"Found: {actual_count} images")
    if actual_count == 112:
        print("✓ PASS")
    else:
        errors.append(f"Image count mismatch: expected 112, found {actual_count}")
        print("✗ FAIL")

    # 2. Check image readability
    print("\n2. IMAGE READABILITY CHECK")
    print("-" * 70)
    unreadable = []
    for img_file in image_files:
        try:
            img = Image.open(img_file)
            img.verify()
        except Exception as e:
            unreadable.append((img_file.name, str(e)))

    if unreadable:
        print(f"✗ FAIL - {len(unreadable)} unreadable images:")
        for fname, error in unreadable:
            print(f"  {fname}: {error}")
            errors.append(f"Unreadable image: {fname}")
    else:
        print(f"✓ PASS - All {actual_count} images are readable")

    # 3. Check for duplicates
    print("\n3. DUPLICATE DETECTION")
    print("-" * 70)
    file_hashes = {}
    duplicates = []

    for img_file in image_files:
        file_hash = get_file_hash(str(img_file))
        if file_hash:
            if file_hash in file_hashes:
                duplicates.append((img_file.name, file_hashes[file_hash]))
            else:
                file_hashes[file_hash] = img_file.name

    if duplicates:
        print(f"✗ FAIL - Found {len(duplicates)} duplicate images:")
        for dup, original in duplicates:
            print(f"  {dup} duplicates {original}")
            errors.append(f"Duplicate found: {dup} = {original}")
    else:
        print(f"✓ PASS - No duplicate images found (all {actual_count} are unique)")

    # 4. Check banks representation
    print("\n4. BANK REPRESENTATION")
    print("-" * 70)
    expected_banks = {'AXIS BANK', 'CANARA BANK', 'ICICI BANK', 'SYNDICATE BANK'}

    if not manifest_path.exists():
        print("✗ FAIL - Manifest file not found")
        errors.append("Manifest file not found")
    else:
        try:
            manifest_df = pd.read_csv(manifest_path)
            banks_in_manifest = set(manifest_df['bank'].unique())

            print(f"Expected banks: {', '.join(sorted(expected_banks))}")
            print(f"Found banks: {', '.join(sorted(banks_in_manifest))}")

            missing_banks = expected_banks - banks_in_manifest
            extra_banks = banks_in_manifest - expected_banks

            if missing_banks:
                print(f"✗ FAIL - Missing banks: {missing_banks}")
                errors.append(f"Missing banks: {missing_banks}")
            elif extra_banks:
                print(f"⚠ WARNING - Unexpected banks: {extra_banks}")
                warnings.append(f"Unexpected banks: {extra_banks}")
            else:
                print("✓ PASS - All 4 expected banks represented")

            # Show bank distribution
            print("\nBank distribution in manifest:")
            for bank, count in manifest_df['bank'].value_counts().items():
                print(f"  {bank}: {count}")
        except Exception as e:
            print(f"✗ FAIL - Error reading manifest: {e}")
            errors.append(f"Error reading manifest: {e}")

    # 5. Manifest entries vs actual files
    print("\n5. MANIFEST-IMAGE CONSISTENCY")
    print("-" * 70)

    if manifest_path.exists():
        try:
            manifest_df = pd.read_csv(manifest_path)

            # Check if all images have manifest entries
            actual_files = {int(f.stem.split()[-1]) for f in image_files}
            manifest_ids = {int(cid) for cid in manifest_df['cheque_id'].unique()}

            missing_in_manifest = actual_files - manifest_ids
            missing_in_images = manifest_ids - actual_files

            print(f"Manifest entries: {len(manifest_df)}")
            print(f"Image files: {len(image_files)}")

            if missing_in_manifest:
                print(f"✗ Images without manifest entries: {missing_in_manifest}")
                errors.append(f"Images without manifest: {missing_in_manifest}")

            if missing_in_images:
                print(f"✗ Manifest entries without images: {missing_in_images}")
                errors.append(f"Manifest without images: {missing_in_images}")

            if not missing_in_manifest and not missing_in_images:
                print("✓ PASS - All images have manifest entries and vice versa")

                # Verify path correctness
                missing_paths = []
                for _, row in manifest_df.iterrows():
                    if not Path(row['image_path']).exists():
                        missing_paths.append(row['image_path'])

                if missing_paths:
                    print(f"✗ Manifest paths don't exist: {missing_paths[:3]}")
                    errors.append(f"Invalid paths in manifest: {len(missing_paths)}")
                else:
                    print("✓ PASS - All manifest paths are valid")
        except Exception as e:
            print(f"✗ FAIL - Error checking manifest: {e}")
            errors.append(f"Error checking manifest: {e}")

    # 6. File integrity (check original vs copied)
    print("\n6. FILE INTEGRITY CHECK")
    print("-" * 70)

    if original_images_dir.exists():
        modified_files = []

        # Compare file sizes between original and copied
        for original_file in original_images_dir.glob('*.tif'):
            copied_file = images_dir / original_file.name

            if copied_file.exists():
                orig_size = original_file.stat().st_size
                copy_size = copied_file.stat().st_size

                if orig_size != copy_size:
                    modified_files.append(f"{original_file.name} (orig: {orig_size}, copy: {copy_size})")
            else:
                errors.append(f"Missing copied file: {original_file.name}")

        if modified_files:
            print(f"✗ FAIL - File sizes differ (possible modification):")
            for f in modified_files[:5]:
                print(f"  {f}")
            if len(modified_files) > 5:
                print(f"  ... and {len(modified_files) - 5} more")
            errors.append(f"File size mismatches: {len(modified_files)}")
        else:
            print("✓ PASS - No file modifications detected")
    else:
        warnings.append("Original dataset folder not found for comparison")
        print("⚠ WARNING - Cannot verify file integrity (original not found)")

    # 7. Metadata verification
    print("\n7. METADATA VERIFICATION")
    print("-" * 70)

    if manifest_path.exists():
        try:
            manifest_df = pd.read_csv(manifest_path)

            # Check required columns
            required_columns = [
                'cheque_id', 'image_path', 'bank', 'image_format', 'width', 'height', 'dpi',
                'user1', 'pen1', 'user2', 'pen2', 'handwritten_text_1', 'handwritten_text_2',
                'source_dataset', 'parent_id', 'label'
            ]

            missing_cols = [col for col in required_columns if col not in manifest_df.columns]
            if missing_cols:
                print(f"✗ FAIL - Missing columns: {missing_cols}")
                errors.append(f"Missing columns in manifest: {missing_cols}")
            else:
                print("✓ PASS - All required columns present")

            # Check label values
            invalid_labels = manifest_df[~manifest_df['label'].isin(['reference'])]['label'].unique()
            if len(invalid_labels) > 0:
                print(f"✗ FAIL - Invalid labels: {invalid_labels}")
                errors.append(f"Invalid labels: {invalid_labels}")
            else:
                print("✓ PASS - All labels are 'reference'")

            # Check image dimensions
            invalid_dims = manifest_df[(manifest_df['width'] < 2000) | (manifest_df['height'] < 1000)]
            if len(invalid_dims) > 0:
                print(f"⚠ WARNING - Some unexpected dimensions: {len(invalid_dims)} entries")
                warnings.append(f"Unexpected dimensions: {len(invalid_dims)} entries")
            else:
                print("✓ PASS - Image dimensions within expected range")

            # Check DPI
            if (manifest_df['dpi'] == 300).all():
                print("✓ PASS - All images marked as 300 DPI")
            else:
                print("⚠ WARNING - Some images have unexpected DPI values")
                warnings.append("Unexpected DPI values found")
        except Exception as e:
            print(f"✗ FAIL - Error verifying metadata: {e}")
            errors.append(f"Metadata verification error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    print(f"Total Errors: {len(errors)}")
    print(f"Total Warnings: {len(warnings)}")

    if errors:
        print("\nErrors:")
        for i, error in enumerate(errors, 1):
            print(f"  {i}. {error}")

    if warnings:
        print("\nWarnings:")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")

    if not errors and not warnings:
        print("\n✓ ALL VALIDATIONS PASSED")
        return 0
    elif errors:
        print("\n✗ VALIDATION FAILED")
        return 1
    else:
        print("\n⚠ VALIDATION PASSED WITH WARNINGS")
        return 0

if __name__ == '__main__':
    exit_code = validate_dataset()
    sys.exit(exit_code)
