#!/usr/bin/env python3
"""
Phase 3 Data Validation Script
Run all data loader checks before proceeding to model implementation
"""

import sys
from pathlib import Path

# Add phase3 to path
sys.path.insert(0, str(Path(__file__).parent))

from data.data_loader import DataLoader

if __name__ == "__main__":
    loader = DataLoader()

    print("\nLoading CSV files...")
    train_df, val_df, test_df = loader.load_splits()

    print("\nRunning comprehensive validation...")
    validation_passed = loader.run_full_validation()

    if validation_passed:
        print("\nBANK DISTRIBUTION SUMMARY")
        print("="*70)

        for split_name in ['train', 'validation', 'test']:
            print(f"\n{split_name.upper()}:")
            dist = loader.get_bank_distribution(split_name)
            for bank, counts in sorted(dist.items()):
                print(f"  {bank}: {counts['parents']} parents, {counts['images']} images")

        print("\n" + "="*70)
        print("✅ DATA VALIDATION COMPLETE - READY FOR PHASE 3")
        print("="*70 + "\n")
    else:
        print("\n" + "="*70)
        print("❌ DATA VALIDATION FAILED")
        print("="*70 + "\n")
        sys.exit(1)
