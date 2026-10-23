"""
Pseudo-Label Pipeline
Orchestrates end-to-end proposal generation with validation
"""

import csv
import json
from pathlib import Path
from typing import Dict, Tuple
import logging
import sys

from ocr_proposal_generator import OCRProposalGenerator
from variant_propagation_manager import VariantPropagationManager
from pseudo_label_validator import (
    validate_box, validate_yolo_label, ValidationReporter
)

# Add extraction module to path
sys.path.insert(0, str(Path(__file__).parent / 'extraction'))
from cheque_field_extractor_v2 import ChequeFieldExtractorV2

logger = logging.getLogger(__name__)


class PseudoLabelPipeline:
    """Orchestrate pseudo-label generation with validation"""

    def __init__(self, train_csv_path: str, project_root: str, output_dir: str):
        """
        Initialize pipeline

        Args:
            train_csv_path: Path to train.csv
            project_root: Project root directory
            output_dir: Output directory for pseudo-labels
        """
        self.train_csv_path = Path(train_csv_path)
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)

        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / 'yolo' / 'train').mkdir(parents=True, exist_ok=True)

        # Initialize components
        self.extractor = ChequeFieldExtractorV2()
        self.ocr_gen = OCRProposalGenerator()
        self.propagation_mgr = VariantPropagationManager(
            str(train_csv_path), str(project_root)
        )

        # Load train.csv
        self.train_images = self._load_train_csv()
        logger.info(f"Loaded {len(self.train_images)} approved training images")

        # Initialize results tracking
        self.stats = self._init_stats()

    def _load_train_csv(self) -> Dict[str, Dict]:
        """Load train.csv into memory"""
        images = {}
        try:
            with open(self.train_csv_path, 'r', encoding='utf-8') as f:
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

                    images[uid] = {
                        'image_path': image_path,
                        'parent_id': parent_id,
                        'label': row.get('label', ''),
                        'forgery_type': row.get('forgery_type', 'none'),
                        'bank': row.get('bank', ''),
                    }
            return images
        except Exception as e:
            logger.error(f"Failed to load train.csv: {e}")
            return {}

    def _init_stats(self) -> Dict:
        """Initialize statistics tracking"""
        return {
            'template_proposals': {'successful': 0, 'failed': 0, 'reasons': {}},
            'ocr_proposals': {'successful': 0, 'failed': 0, 'text_regions': 0},
            'fusion': {'both_methods': 0, 'template_only': 0, 'ocr_only': 0, 'neither': 0},
            'propagation': {'successful': 0, 'failed': 0, 'alignment_uncertain': 0},
            'validation': {
                'boxes_valid': 0,
                'boxes_invalid': 0,
                'yolo_valid': 0,
                'yolo_invalid': 0,
                'invalid_reasons': {}
            },
            'per_field_coverage': {}
        }

    def generate_template_proposals(self) -> Dict[str, Dict]:
        """Generate proposals using template regions"""
        logger.info("Generating template-based proposals...")
        proposals = {}

        for uid, img_info in self.train_images.items():
            image_path = self.project_root / img_info['image_path']

            if not image_path.exists():
                logger.warning(f"Image not found: {image_path}")
                self.stats['template_proposals']['failed'] += 1
                continue

            try:
                import cv2
                img = cv2.imread(str(image_path))
                if img is None:
                    raise ValueError("Cannot decode image")

                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                results = self.extractor.extract_fields(img_rgb)

                field_proposals = {}
                for field_name, result in results.items():
                    if result.detected and result.region_bounds:
                        h, w = img.shape[:2]
                        x_min, y_min, x_max, y_max = result.region_bounds

                        box = [
                            x_min / w,
                            y_min / h,
                            (x_max - x_min) / w,
                            (y_max - y_min) / h
                        ]

                        field_proposals[field_name] = {
                            'box': box,
                            'method': 'template',
                            'confidence': result.confidence,
                            'evidence': f'Template region detection. Content score: {result.confidence:.2f}.'
                        }

                if field_proposals:
                    proposals[uid] = field_proposals
                    self.stats['template_proposals']['successful'] += 1
                else:
                    self.stats['template_proposals']['failed'] += 1
                    self.stats['template_proposals']['reasons']['no_content'] = \
                        self.stats['template_proposals']['reasons'].get('no_content', 0) + 1

            except Exception as e:
                logger.error(f"Template generation failed for {uid}: {e}")
                self.stats['template_proposals']['failed'] += 1
                reason = type(e).__name__
                self.stats['template_proposals']['reasons'][reason] = \
                    self.stats['template_proposals']['reasons'].get(reason, 0) + 1

        logger.info(f"Template proposals: {self.stats['template_proposals']['successful']}/{len(self.train_images)}")
        return proposals

    def generate_ocr_proposals(self) -> Dict[str, Dict]:
        """Generate proposals using OCR"""
        logger.info("Generating OCR-based proposals...")
        proposals = {}

        for uid, img_info in self.train_images.items():
            image_path = self.project_root / img_info['image_path']

            if not image_path.exists():
                self.stats['ocr_proposals']['failed'] += 1
                continue

            try:
                field_proposals = self.ocr_gen.generate_proposals(str(image_path))

                if field_proposals:
                    proposals[uid] = field_proposals
                    self.stats['ocr_proposals']['successful'] += 1
                    text_count = len(field_proposals.get('_unclassified_text', []))
                    self.stats['ocr_proposals']['text_regions'] += \
                        len([f for f in field_proposals if not f.startswith('_')]) + text_count
                else:
                    self.stats['ocr_proposals']['failed'] += 1

            except Exception as e:
                logger.error(f"OCR generation failed for {uid}: {e}")
                self.stats['ocr_proposals']['failed'] += 1

        logger.info(f"OCR proposals: {self.stats['ocr_proposals']['successful']}/{len(self.train_images)}")
        return proposals

    def fuse_proposals(self, template_dict: Dict, ocr_dict: Dict) -> Dict:
        """Fuse template and OCR proposals"""
        logger.info("Fusing proposals...")
        fused = {}

        for uid in self.train_images.keys():
            template_props = template_dict.get(uid, {})
            ocr_props = ocr_dict.get(uid, {})

            # Fuse fields
            fused_fields = {}
            fields_seen = set(template_props.keys()) | set(ocr_props.keys())
            fields_seen.discard('_unclassified_text')

            for field in fields_seen:
                template_field = template_props.get(field)
                ocr_field = ocr_props.get(field)

                if template_field and ocr_field:
                    # Both methods available - average confidence, take best box
                    template_conf = template_field.get('confidence', 0)
                    ocr_conf = ocr_field.get('classification_confidence')
                    ocr_conf_num = {'high': 0.9, 'medium': 0.7, 'low': 0.5}.get(ocr_conf, 0)

                    fused_confidence = (template_conf + ocr_conf_num) / 2

                    # Take box from higher confidence source
                    if ocr_conf_num >= template_conf:
                        box = ocr_field.get('box')
                        source = 'ocr'
                    else:
                        box = template_field.get('box')
                        source = 'template'

                    fused_fields[field] = {
                        'box': box,
                        'methods': ['template', 'ocr'],
                        'confidence': fused_confidence,
                        'method_sources': {
                            'template': template_field.get('confidence'),
                            'ocr': ocr_conf
                        },
                        'evidence': f'Fused: template ({template_conf:.2f}) + ocr ({ocr_conf_num:.2f}). Box from {source}.'
                    }
                    self.stats['fusion']['both_methods'] += 1

                elif template_field:
                    fused_fields[field] = {**template_field, 'methods': ['template']}
                    self.stats['fusion']['template_only'] += 1

                elif ocr_field:
                    fused_fields[field] = {**ocr_field, 'methods': ['ocr']}
                    self.stats['fusion']['ocr_only'] += 1

            if not fused_fields:
                self.stats['fusion']['neither'] += 1
            else:
                fused[uid] = fused_fields

        logger.info(f"Fused: both={self.stats['fusion']['both_methods']}, "
                   f"template={self.stats['fusion']['template_only']}, "
                   f"ocr={self.stats['fusion']['ocr_only']}")
        return fused

    def propagate_variants(self, reference_proposals: Dict) -> Dict:
        """Propagate to variants with validation"""
        logger.info("Propagating to variants...")

        variant_props = self.propagation_mgr.process_all_variants(reference_proposals)

        self.stats['propagation']['successful'] = \
            sum(1 for v in variant_props.values()
                if v.get('alignment_check', {}).get('is_aligned', False))
        self.stats['propagation']['alignment_uncertain'] = \
            len(variant_props) - self.stats['propagation']['successful']

        logger.info(f"Propagated: {self.stats['propagation']['successful']} aligned, "
                   f"{self.stats['propagation']['alignment_uncertain']} uncertain")
        return variant_props

    def validate_all_proposals(self, all_proposals: Dict) -> Tuple[Dict, Dict]:
        """
        Validate all generated proposals

        Returns:
            (valid_proposals, validation_details)
        """
        logger.info("Validating proposals...")
        valid_proposals = {}
        validation_details = {
            'total': 0,
            'valid': 0,
            'invalid': 0,
            'failures': []
        }

        for uid, fields_dict in all_proposals.items():
            valid_fields = {}

            for field_name, field_data in fields_dict.items():
                if field_name.startswith('_') or field_name == 'fields':
                    continue

                box = field_data.get('box')
                if not box:
                    continue

                validation_details['total'] += 1

                # Validate box
                is_valid, reason = validate_box(box)

                if is_valid:
                    valid_fields[field_name] = field_data
                    self.stats['validation']['boxes_valid'] += 1
                    validation_details['valid'] += 1

                    # Track per-field coverage
                    if field_name not in self.stats['per_field_coverage']:
                        self.stats['per_field_coverage'][field_name] = 0
                    self.stats['per_field_coverage'][field_name] += 1
                else:
                    self.stats['validation']['boxes_invalid'] += 1
                    validation_details['invalid'] += 1
                    self.stats['validation']['invalid_reasons'][reason] = \
                        self.stats['validation']['invalid_reasons'].get(reason, 0) + 1
                    validation_details['failures'].append({
                        'uid': uid,
                        'field': field_name,
                        'reason': reason
                    })

            if valid_fields:
                # Copy metadata fields
                valid_proposals[uid] = {
                    'image_path': all_proposals[uid].get('image_path'),
                    'label_source': all_proposals[uid].get('label_source'),
                    'is_verified': False,
                    'fields': valid_fields
                }

                # Copy optional fields
                for key in ['parent_id', 'forgery_type', 'alignment_check']:
                    if key in all_proposals[uid]:
                        valid_proposals[uid][key] = all_proposals[uid][key]

        logger.info(f"Validation: {validation_details['valid']} valid, "
                   f"{validation_details['invalid']} invalid boxes")
        return valid_proposals, validation_details

    def generate_all_proposals_with_validation(self) -> Dict:
        """Generate all proposals with full validation"""
        logger.info("=" * 70)
        logger.info("PSEUDO-LABEL GENERATION PIPELINE")
        logger.info("=" * 70)

        # Step 1: Template proposals (reference images only)
        logger.info("\n[Step 1] Generating template-based proposals...")
        reference_template = self.generate_template_proposals()

        # Step 2: OCR proposals (reference images only)
        logger.info("\n[Step 2] Generating OCR-based proposals...")
        reference_ocr = self.generate_ocr_proposals()

        # Step 3: Fuse methods for reference images
        logger.info("\n[Step 3] Fusing template + OCR proposals...")
        reference_fused = self.fuse_proposals(reference_template, reference_ocr)

        # Step 4: Propagate to variants
        logger.info("\n[Step 4] Propagating to variant images...")
        variant_proposals = self.propagate_variants(reference_fused)

        # Step 5: Combine all proposals
        logger.info("\n[Step 5] Combining all proposals...")
        all_proposals = {}

        # Add reference proposals
        for uid, fields in reference_fused.items():
            all_proposals[uid] = {
                'image_path': self.train_images[uid]['image_path'],
                'label_source': 'hybrid_proposal',
                'is_verified': False,
                'fields': fields
            }

        # Add variant proposals
        for uid, props in variant_proposals.items():
            all_proposals[uid] = props

        # Step 6: Validate all proposals
        logger.info("\n[Step 6] Validating proposals...")
        valid_proposals, val_details = self.validate_all_proposals(all_proposals)

        logger.info("\n" + "=" * 70)
        logger.info("GENERATION COMPLETE")
        logger.info("=" * 70)

        return valid_proposals

    def save_metadata(self, proposals: Dict):
        """Save proposals to metadata.json"""
        logger.info("\nSaving metadata...")
        metadata_file = self.output_dir / 'metadata.json'

        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(proposals, f, indent=2)

        logger.info(f"Saved metadata: {metadata_file}")

    def export_yolo_format_validated(self, proposals: Dict):
        """Export YOLO format with validation"""
        logger.info("\nExporting YOLO format...")

        field_to_class = {
            'cheque_number': 0,
            'bank_name': 1,
            'account_number': 2,
            'date': 3,
            'payee_name': 4,
            'amount': 5,
            'signature': 6,
            'micr_code': 7
        }

        exported = 0
        skipped = 0
        yolo_stats = {
            'class_distribution': {}
        }

        for uid, props in proposals.items():
            fields = props.get('fields', {})

            yolo_lines = []
            for field_name, field_data in fields.items():
                if field_name not in field_to_class:
                    continue

                box = field_data.get('box')
                if not box:
                    continue

                x_min, y_min, width, height = box
                x_center = x_min + width / 2
                y_center = y_min + height / 2

                class_id = field_to_class[field_name]

                # Validate YOLO label
                is_valid, reason = validate_yolo_label(class_id, x_center, y_center, width, height)

                if is_valid:
                    yolo_lines.append(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
                    self.stats['validation']['yolo_valid'] += 1

                    if class_id not in yolo_stats['class_distribution']:
                        yolo_stats['class_distribution'][class_id] = 0
                    yolo_stats['class_distribution'][class_id] += 1
                else:
                    self.stats['validation']['yolo_invalid'] += 1
                    logger.debug(f"Invalid YOLO label for {uid}.{field_name}: {reason}")

            if yolo_lines:
                yolo_file = self.output_dir / 'yolo' / 'train' / f'{uid}.txt'
                with open(yolo_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(yolo_lines) + '\n')
                exported += 1
            else:
                skipped += 1

        logger.info(f"YOLO export: {exported} files created, {skipped} skipped (no valid labels)")
        return yolo_stats

    def generate_validation_report(self) -> Dict:
        """Generate comprehensive validation report"""
        report = {
            'input': {
                'total_approved_images': len(self.train_images),
                'reference_images': sum(1 for img in self.train_images.values()
                                       if img['label'] == 'reference'),
                'variant_images': sum(1 for img in self.train_images.values()
                                     if img['label'] != 'reference'),
            },
            'template_proposals': self.stats['template_proposals'],
            'ocr_proposals': self.stats['ocr_proposals'],
            'fusion': self.stats['fusion'],
            'propagation': self.stats['propagation'],
            'validation': self.stats['validation'],
            'per_field_coverage': self.stats['per_field_coverage'],
            'note': {
                'geometric_validation': 'Checks that box coordinates are valid normalized values.',
                'semantic_validation': 'NOT PERFORMED. Passing geometric validation does NOT mean box identifies correct field.',
                'forged_fields': 'Fields flagged as forged are marked unreliable and should not be used for training.',
                'alignment_uncertain': 'Variant proposals flagged as alignment_uncertain have reduced confidence due to dimension/layout mismatches.'
            }
        }
        return report


def main():
    """Run pipeline"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(message)s'
    )

    project_root = Path('C:/Users/Rushmitha/OneDrive/Desktop/cheque')
    train_csv = project_root / 'datasets/splits/train.csv'
    output_dir = project_root / 'phase3/data/pseudo_labels'

    pipeline = PseudoLabelPipeline(str(train_csv), str(project_root), str(output_dir))

    # Generate proposals
    proposals = pipeline.generate_all_proposals_with_validation()

    # Save results
    pipeline.save_metadata(proposals)
    yolo_stats = pipeline.export_yolo_format_validated(proposals)

    # Generate report
    report = pipeline.generate_validation_report()
    report_file = output_dir / 'validation_report.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    logger.info(f"\nReport saved: {report_file}")
    logger.info("\n" + json.dumps(report, indent=2))

    return pipeline, report


if __name__ == '__main__':
    main()
