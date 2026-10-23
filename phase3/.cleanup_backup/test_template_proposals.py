"""
Test Template-Based Proposal Generation
Safe test using only ChequeFieldExtractorV2 (no OCR dependencies)
"""

import csv
import json
from pathlib import Path
import sys
import cv2
import logging

sys.path.insert(0, str(Path(__file__).parent / 'extraction'))
from cheque_field_extractor_v2 import ChequeFieldExtractorV2

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def generate_template_proposals_safe(test_size=10):
    """
    Generate template proposals for a sample of images

    Args:
        test_size: Number of images to test

    Returns:
        (proposals_dict, statistics)
    """

    project_root = Path('C:/Users/Rushmitha/OneDrive/Desktop/cheque')
    train_csv = project_root / 'datasets/splits/train.csv'
    output_dir = project_root / 'phase3/data/pseudo_labels'

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 70)
    logger.info("TEST: TEMPLATE-BASED PROPOSAL GENERATION")
    logger.info("=" * 70)

    # Load train.csv
    train_images = {}
    with open(train_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            image_path = row.get('image_path', '')
            parent_id = row.get('parent_id', '')

            # Extract UID
            stem = Path(image_path).stem
            if '_forgery' in stem.lower():
                uid = stem
            else:
                uid = f"{parent_id}_reference"

            train_images[uid] = {
                'image_path': image_path,
                'parent_id': parent_id,
                'label': row.get('label', ''),
                'forgery_type': row.get('forgery_type', 'none'),
                'bank': row.get('bank', ''),
            }

    logger.info(f"\nLoaded {len(train_images)} approved training images from train.csv")

    # Initialize extractor
    extractor = ChequeFieldExtractorV2()

    # Generate proposals for sample
    proposals = {}
    stats = {
        'total_tested': 0,
        'successful': 0,
        'failed': 0,
        'failures': [],
        'fields_found': {},
        'sample_uids': []
    }

    logger.info(f"\nGenerating template proposals for {test_size} sample images...")
    logger.info("-" * 70)

    tested_count = 0
    for uid, img_info in train_images.items():
        if tested_count >= test_size:
            break

        image_path = project_root / img_info['image_path']
        stats['total_tested'] += 1
        stats['sample_uids'].append(uid)

        logger.info(f"\n[{tested_count + 1}/{test_size}] {uid}")
        logger.info(f"  Image: {image_path.name}")
        logger.info(f"  Path exists: {image_path.exists()}")

        if not image_path.exists():
            logger.warning(f"  ERROR: Image not found")
            stats['failed'] += 1
            stats['failures'].append({'uid': uid, 'error': 'Image not found'})
            tested_count += 1
            continue

        try:
            # Read image
            img = cv2.imread(str(image_path))
            if img is None:
                raise ValueError("Cannot decode image")

            # Convert to RGB
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            height, width = img.shape[:2]

            logger.info(f"  Dimensions: {width}x{height}")

            # Extract fields
            results = extractor.extract_fields(img_rgb)

            # Build proposals
            field_proposals = {}
            for field_name, result in results.items():
                if result.detected and result.region_bounds:
                    x_min, y_min, x_max, y_max = result.region_bounds

                    # Normalize coordinates
                    box = [
                        x_min / width,
                        y_min / height,
                        (x_max - x_min) / width,
                        (y_max - y_min) / height
                    ]

                    # Validate box
                    if all(0 <= c <= 1 for c in [box[0], box[1]]) and \
                       all(c > 0 for c in [box[2], box[3]]) and \
                       box[0] + box[2] <= 1 and box[1] + box[3] <= 1:

                        field_proposals[field_name] = {
                            'box': box,
                            'method': 'template',
                            'confidence': round(result.confidence, 2),
                            'evidence': f'Template region. Content score: {result.confidence:.2f}.'
                        }

                        # Track field
                        if field_name not in stats['fields_found']:
                            stats['fields_found'][field_name] = 0
                        stats['fields_found'][field_name] += 1

                        logger.info(f"    {field_name:20}: confidence={result.confidence:.2f}")
                else:
                    logger.info(f"    {field_name:20}: not detected")

            if field_proposals:
                proposals[uid] = {
                    'image_path': img_info['image_path'],
                    'label_source': 'template_proposal',
                    'is_verified': False,
                    'fields': field_proposals
                }
                stats['successful'] += 1
                logger.info(f"  Result: {len(field_proposals)} fields proposed")
            else:
                stats['failed'] += 1
                logger.info(f"  Result: No fields detected")
                stats['failures'].append({'uid': uid, 'error': 'No fields detected'})

        except Exception as e:
            logger.error(f"  ERROR: {e}")
            stats['failed'] += 1
            stats['failures'].append({'uid': uid, 'error': str(e)})

        tested_count += 1

    return proposals, stats


def generate_report(proposals, stats):
    """Generate and save test report"""

    project_root = Path('C:/Users/Rushmitha/OneDrive/Desktop/cheque')
    output_dir = project_root / 'phase3/data/pseudo_labels'

    report = {
        'test_type': 'Template-based proposal generation (safe test)',
        'reason': 'OCR requires pytesseract/Tesseract which cannot be installed. This test demonstrates pipeline logic with template regions only.',
        'input': {
            'total_approved_images': 315,
            'sample_tested': stats['total_tested'],
            'sample_uids': stats['sample_uids']
        },
        'results': {
            'successful_proposals': stats['successful'],
            'failed_proposals': stats['failed'],
            'total_fields_generated': sum(stats['fields_found'].values())
        },
        'per_field_results': {
            field_name: {
                'proposed_in_sample': count,
                'percent_of_sample': round(count / stats['successful'] * 100, 1) if stats['successful'] > 0 else 0
            }
            for field_name, count in sorted(stats['fields_found'].items())
        },
        'failures': stats['failures'],
        'next_steps': [
            '1. Evaluate template proposal quality on this sample',
            '2. Review metadata.json for detailed proposals',
            '3. For production: Add OCR support (requires pytesseract + Tesseract system binary)',
            '4. For production: Implement variant propagation as designed',
            '5. Validate YOLO format and train when approved'
        ],
        'important_notes': [
            'GEOMETRIC validation only: Box coordinates are valid',
            'SEMANTIC validation: NOT PERFORMED - passing geometric checks does NOT prove correctness',
            'All proposals marked is_verified: false',
            'Forged-field handling: Not applicable for template method (no field assignment logic)',
            'This is a safe test that respects the "no package installation" constraint'
        ]
    }

    # Save report
    report_file = output_dir / 'test_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    # Save sample proposals
    metadata_file = output_dir / 'test_sample_metadata.json'
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(proposals, f, indent=2)

    # Print report
    logger.info("\n" + "=" * 70)
    logger.info("TEST RESULTS REPORT")
    logger.info("=" * 70)
    logger.info(json.dumps(report, indent=2))

    logger.info("\n" + "=" * 70)
    logger.info("OUTPUT FILES")
    logger.info("=" * 70)
    logger.info(f"Test report:      {report_file}")
    logger.info(f"Sample proposals: {metadata_file}")
    logger.info("\nBoth files available for review.")

    return report


def main():
    """Run test"""
    proposals, stats = generate_template_proposals_safe(test_size=10)
    report = generate_report(proposals, stats)

    logger.info("\n" + "=" * 70)
    logger.info("SUMMARY")
    logger.info("=" * 70)
    logger.info(f"Sample size:            {stats['total_tested']}")
    logger.info(f"Successful proposals:   {stats['successful']}")
    logger.info(f"Failed proposals:       {stats['failed']}")
    logger.info(f"Total fields generated: {sum(stats['fields_found'].values())}")
    logger.info("\nField distribution:")
    for field, count in sorted(stats['fields_found'].items()):
        logger.info(f"  {field:25}: {count}")

    if stats['failures']:
        logger.info("\nFailures:")
        for fail in stats['failures']:
            logger.info(f"  {fail['uid']:30}: {fail['error']}")

    logger.info("\n" + "=" * 70)
    logger.info("IMPORTANT: This is a LIMITED test using template regions only.")
    logger.info("Full pipeline requires OCR (pytesseract + Tesseract binary)")
    logger.info("=" * 70)


if __name__ == '__main__':
    main()
