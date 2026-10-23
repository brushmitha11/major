"""
Variant Propagation Manager
Propagates proposals from parent reference images to forgery variants
with alignment validation
"""

import csv
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Tuple, List
import logging
import json

logger = logging.getLogger(__name__)


class VariantPropagationManager:
    """Manage propagation of proposals from parents to variants"""

    def __init__(self, train_csv_path: str, project_root: str):
        """
        Initialize propagation manager

        Args:
            train_csv_path: Path to train.csv
            project_root: Project root directory
        """
        self.train_csv_path = Path(train_csv_path)
        self.project_root = Path(project_root)
        self.parent_variants = self._load_parent_variant_mapping()
        logger.info(f"Loaded {len(self.parent_variants)} parent-variant mappings")

    def _load_parent_variant_mapping(self) -> Dict[str, List[Dict]]:
        """
        Load mapping of parent -> variants from train.csv

        Returns:
            {parent_id: [
              {
                'uid': '309137_reference',
                'image_path': 'datasets/raw/...',
                'label': 'reference',
                'forgery_type': 'none'
              },
              {
                'uid': '309137_amount_forgery',
                'image_path': 'datasets/synthetic/...',
                'label': 'synthetic_forgery',
                'forgery_type': 'amount_forgery'
              },
              ...
            ]}
        """
        mapping = {}

        try:
            with open(self.train_csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    parent_id = row.get('parent_id', '')
                    image_path = row.get('image_path', '')
                    label = row.get('label', '')
                    forgery_type = row.get('forgery_type', 'none')

                    # Extract UID from image path
                    stem = Path(image_path).stem
                    if '_forgery' in stem.lower():
                        uid = stem
                    else:
                        uid = f"{parent_id}_reference"

                    if parent_id not in mapping:
                        mapping[parent_id] = []

                    mapping[parent_id].append({
                        'uid': uid,
                        'image_path': image_path,
                        'label': label,
                        'forgery_type': forgery_type
                    })

            return mapping
        except Exception as e:
            logger.error(f"Failed to load parent-variant mapping: {e}")
            return {}

    def check_alignment(self, parent_image_path: str, variant_image_path: str) -> Dict:
        """
        Check if variant image is geometrically aligned with parent
        Beyond dimensions, checks if layout appears unchanged

        Args:
            parent_image_path: Path to parent image
            variant_image_path: Path to variant image

        Returns:
            {
              'is_aligned': bool,
              'dimension_check': {...},
              'alignment_confidence': 'high|medium|low|unknown',
              'notes': 'explanation'
            }
        """
        alignment_result = {
            'is_aligned': False,
            'dimension_check': {},
            'alignment_confidence': 'unknown',
            'notes': ''
        }

        try:
            parent_img = cv2.imread(str(parent_image_path))
            variant_img = cv2.imread(str(variant_image_path))

            if parent_img is None or variant_img is None:
                alignment_result['notes'] = 'Cannot read image(s)'
                return alignment_result

            parent_h, parent_w = parent_img.shape[:2]
            variant_h, variant_w = variant_img.shape[:2]

            # Step 1: Dimension check
            dim_diff_w = abs(parent_w - variant_w) / parent_w * 100
            dim_diff_h = abs(parent_h - variant_h) / parent_h * 100

            alignment_result['dimension_check'] = {
                'parent': f'{parent_w}x{parent_h}',
                'variant': f'{variant_w}x{variant_h}',
                'diff_width_percent': round(dim_diff_w, 1),
                'diff_height_percent': round(dim_diff_h, 1)
            }

            # Step 2: Layout alignment check via structural similarity
            # Convert to grayscale and compare edge patterns
            try:
                parent_gray = cv2.cvtColor(parent_img, cv2.COLOR_BGR2GRAY)
                variant_gray = cv2.cvtColor(variant_img, cv2.COLOR_BGR2GRAY)

                # Resize variant to parent size if needed for comparison
                if parent_gray.shape != variant_gray.shape:
                    variant_gray_resized = cv2.resize(variant_gray, (parent_w, parent_h))
                else:
                    variant_gray_resized = variant_gray

                # Compute structural similarity via SSIM approximation
                # (Use absolute difference of Canny edges as layout similarity)
                parent_edges = cv2.Canny(parent_gray, 100, 200)
                variant_edges = cv2.Canny(variant_gray_resized, 100, 200)

                # Count matching edge pixels
                matching_edges = np.sum((parent_edges > 0) & (variant_edges > 0))
                total_edges = np.sum(parent_edges > 0)

                if total_edges > 0:
                    edge_match_ratio = matching_edges / total_edges
                else:
                    edge_match_ratio = 0

                alignment_result['edge_match_ratio'] = round(edge_match_ratio, 3)

            except Exception as e:
                logger.debug(f"Edge matching failed: {e}")
                alignment_result['edge_match_ratio'] = None

            # Step 3: Determine alignment confidence
            if dim_diff_w < 2 and dim_diff_h < 2:
                # Dimensions nearly identical
                if alignment_result.get('edge_match_ratio', 0) > 0.7:
                    alignment_result['is_aligned'] = True
                    alignment_result['alignment_confidence'] = 'high'
                    alignment_result['notes'] = 'Dimensions match, layout unchanged (high confidence)'
                else:
                    alignment_result['is_aligned'] = True
                    alignment_result['alignment_confidence'] = 'medium'
                    alignment_result['notes'] = f'Dimensions match, layout partially changed (edge match: {alignment_result.get("edge_match_ratio", 0):.1%})'
            elif dim_diff_w < 5 and dim_diff_h < 5:
                # Dimensions close
                alignment_result['is_aligned'] = True
                alignment_result['alignment_confidence'] = 'medium'
                alignment_result['notes'] = f'Dimensions differ slightly (W: {dim_diff_w:.1f}%, H: {dim_diff_h:.1f}%)'
            else:
                # Dimensions differ significantly
                alignment_result['is_aligned'] = False
                alignment_result['alignment_confidence'] = 'low'
                alignment_result['notes'] = f'Dimensions differ significantly (W: {dim_diff_w:.1f}%, H: {dim_diff_h:.1f}%). Propagation unreliable.'

            return alignment_result

        except Exception as e:
            logger.error(f"Alignment check failed: {e}")
            alignment_result['notes'] = f'Alignment check error: {e}'
            return alignment_result

    def propagate_to_variant(self, parent_proposals: Dict, parent_id: str,
                            forgery_type: str, alignment_check: Dict) -> Dict:
        """
        Propagate parent proposals to variant with forgery awareness

        Args:
            parent_proposals: Proposals from parent image
            parent_id: Parent image ID
            forgery_type: Type of forgery applied (from train.csv)
            alignment_check: Result from check_alignment()

        Returns:
            {
              'field_name': {
                'box': [...],
                'method': 'propagated',
                'parent_id': '309137',
                'parent_confidence': 0.8,
                'propagated_confidence': 0.15,  # if forged
                'is_reliable': false,
                'forged_field_flag': true,
                'alignment_check': {...},
                'evidence': 'explanation'
              },
              ...
            }
        """
        propagated = {}

        # Determine field modifications from forgery type
        forged_fields = self._get_forged_fields(forgery_type)

        for field_name, parent_field in parent_proposals.items():
            # Skip metadata fields
            if field_name.startswith('_'):
                continue

            propagated_field = {
                'box': parent_field.get('box'),
                'method': 'propagated',
                'parent_id': parent_id,
                'parent_confidence': parent_field.get('classification_confidence'),
                'alignment_check': alignment_check,
            }

            # Check if this field was forged
            if field_name in forged_fields:
                # FORGED FIELD - mark as unreliable
                propagated_field['propagated_confidence'] = 0.15
                propagated_field['is_reliable'] = False
                propagated_field['forged_field_flag'] = True
                propagated_field['evidence'] = f'FORGED: Field was modified in variant (forgery_type: {forgery_type}). Box propagated but prediction unreliable.'
                logger.debug(f"  {field_name}: FORGED (confidence: 0.15, unreliable)")
            else:
                # NOT FORGED - inherit parent confidence
                if not alignment_check['is_aligned']:
                    # Alignment uncertain - reduce confidence
                    parent_conf = parent_field.get('classification_confidence')
                    confidence_reduction = 0.3
                    propagated_field['propagated_confidence'] = max(0,
                        (parent_conf_numeric(parent_conf) - confidence_reduction))
                    propagated_field['confidence_note'] = f'Alignment uncertain: {alignment_check["notes"]}. Reduced by {confidence_reduction}.'
                    logger.debug(f"  {field_name}: Propagated (reduced confidence, alignment uncertain)")
                else:
                    propagated_field['propagated_confidence'] = parent_field.get('classification_confidence')
                    logger.debug(f"  {field_name}: Propagated (confidence: {parent_field.get('classification_confidence')})")

                propagated_field['is_reliable'] = True
                propagated_field['forged_field_flag'] = False
                propagated_field['evidence'] = f'Propagated from parent {parent_id}. Not modified in this variant.'

            propagated[field_name] = propagated_field

        return propagated

    def _get_forged_fields(self, forgery_type: str) -> set:
        """Get set of field names that were forged"""
        mapping = {
            'amount_forgery': {'amount'},
            'payee_forgery': {'payee_name'},
            'date_forgery': {'date'},
            'multi_field_forgery': {'amount', 'payee_name', 'date'},
            'none': set()
        }
        return mapping.get(forgery_type, set())

    def process_all_variants(self, reference_proposals: Dict) -> Dict:
        """
        Propagate proposals to all variants

        Args:
            reference_proposals: {uid: proposals} for all reference images

        Returns:
            {uid: propagated_proposals} for all 237 variant images
        """
        variant_proposals = {}
        propagation_stats = {
            'successful': 0,
            'alignment_uncertain': 0,
            'failed': 0,
            'failures': []
        }

        for parent_id, variants in self.parent_variants.items():
            # Find reference image (label == 'reference')
            reference = next((v for v in variants if v['label'] == 'reference'), None)
            if not reference:
                logger.warning(f"No reference image found for parent {parent_id}")
                continue

            parent_ref_uid = reference['uid']
            parent_proposals = reference_proposals.get(parent_ref_uid)
            if not parent_proposals:
                logger.warning(f"No proposals for parent {parent_ref_uid}")
                continue

            # Process each variant
            for variant in variants:
                if variant['label'] == 'reference':
                    continue  # Skip reference itself

                variant_uid = variant['uid']
                forgery_type = variant.get('forgery_type', 'none')

                try:
                    # Get image paths
                    parent_path = self.project_root / reference['image_path']
                    variant_path = self.project_root / variant['image_path']

                    # Check alignment
                    alignment = self.check_alignment(str(parent_path), str(variant_path))

                    # Propagate
                    propagated = self.propagate_to_variant(
                        parent_proposals,
                        parent_id,
                        forgery_type,
                        alignment
                    )

                    variant_proposals[variant_uid] = {
                        'image_path': variant['image_path'],
                        'label_source': 'variant_propagation',
                        'is_verified': False,
                        'parent_id': parent_id,
                        'forgery_type': forgery_type,
                        'alignment_check': alignment,
                        'fields': propagated
                    }

                    if alignment['is_aligned']:
                        propagation_stats['successful'] += 1
                    else:
                        propagation_stats['alignment_uncertain'] += 1

                except Exception as e:
                    logger.error(f"Failed to propagate to {variant_uid}: {e}")
                    propagation_stats['failed'] += 1
                    propagation_stats['failures'].append({
                        'uid': variant_uid,
                        'error': str(e)
                    })

        logger.info(f"Variant propagation: {propagation_stats['successful']} successful, "
                   f"{propagation_stats['alignment_uncertain']} with uncertain alignment, "
                   f"{propagation_stats['failed']} failed")

        return variant_proposals


def parent_conf_numeric(conf_str: str) -> float:
    """Convert confidence string to numeric for calculations"""
    mapping = {'high': 0.9, 'medium': 0.7, 'low': 0.5}
    return mapping.get(conf_str, 0.5)


def test_propagation():
    """Test propagation with actual train.csv"""
    project_root = Path('C:/Users/Rushmitha/OneDrive/Desktop/cheque')
    train_csv = project_root / 'datasets/splits/train.csv'

    manager = VariantPropagationManager(str(train_csv), str(project_root))

    print(f"Loaded {len(manager.parent_variants)} parent groups")

    # Test alignment check on first variant
    for parent_id, variants in list(manager.parent_variants.items())[:1]:
        reference = next((v for v in variants if v['label'] == 'reference'), None)
        variant = next((v for v in variants if v['label'] != 'reference'), None)

        if reference and variant:
            parent_path = project_root / reference['image_path']
            variant_path = project_root / variant['image_path']

            print(f"\nTesting alignment check:")
            print(f"  Parent: {parent_path}")
            print(f"  Variant: {variant_path}")

            alignment = manager.check_alignment(str(parent_path), str(variant_path))
            print(f"\nAlignment result:")
            print(json.dumps(alignment, indent=2))

    return manager


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    test_propagation()
