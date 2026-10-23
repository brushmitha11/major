"""
Pseudo-Label Validator
Validates bounding boxes and YOLO labels
"""

from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def validate_box(box: list, min_size: float = 0.01, max_size: float = 0.95) -> Tuple[bool, str]:
    """
    Validate bounding box coordinates

    GEOMETRIC VALIDATION ONLY - does NOT verify field correctness

    Args:
        box: [x_min, y_min, width, height] in normalized coordinates [0, 1]
        min_size: minimum allowed box dimension
        max_size: maximum allowed box dimension

    Returns:
        (is_valid, reason)
    """
    try:
        if len(box) != 4:
            return False, "Box must have 4 coordinates"

        x_min, y_min, width, height = box

        # Check types
        for val in box:
            if not isinstance(val, (int, float)):
                return False, f"Coordinate must be numeric, got {type(val)}"

        # Check coordinate ranges [0, 1]
        if not (0 <= x_min <= 1):
            return False, f"x_min out of range: {x_min}"

        if not (0 <= y_min <= 1):
            return False, f"y_min out of range: {y_min}"

        # Check dimensions are positive
        if width <= 0 or height <= 0:
            return False, f"Box dimensions must be positive: {width}x{height}"

        # Check dimensions are in valid range
        if width > 1 or height > 1:
            return False, f"Box dimensions cannot exceed 1: {width}x{height}"

        # Check box doesn't extend past boundaries
        if x_min + width > 1:
            return False, f"Box extends past right boundary: x_min={x_min}, width={width}"

        if y_min + height > 1:
            return False, f"Box extends past bottom boundary: y_min={y_min}, height={height}"

        # Check minimum size
        if width < min_size or height < min_size:
            return False, f"Box too small: {width:.4f}x{height:.4f} (min: {min_size})"

        # Check maximum size
        if width > max_size or height > max_size:
            return False, f"Box too large: {width:.4f}x{height:.4f} (max: {max_size})"

        return True, "Valid"

    except Exception as e:
        return False, f"Validation error: {e}"


def validate_yolo_label(class_id: int, x_center: float, y_center: float,
                        width: float, height: float) -> Tuple[bool, str]:
    """
    Validate YOLO format label

    GEOMETRIC VALIDATION ONLY - does NOT verify class assignment correctness

    Args:
        class_id: 0-7 (field class)
        x_center, y_center, width, height: normalized coordinates [0, 1]

    Returns:
        (is_valid, reason)
    """
    try:
        # Check class ID
        if not isinstance(class_id, int):
            return False, f"class_id must be int, got {type(class_id)}"

        if not (0 <= class_id <= 7):
            return False, f"Invalid class_id: {class_id} (must be 0-7)"

        # Check all coordinates are numeric
        for val in [x_center, y_center, width, height]:
            if not isinstance(val, (int, float)):
                return False, f"Coordinate must be numeric, got {type(val)}"

        # Check coordinate ranges [0, 1]
        for name, val in [('x_center', x_center), ('y_center', y_center),
                          ('width', width), ('height', height)]:
            if not (0 <= val <= 1):
                return False, f"{name} out of range: {val}"

        # Check box boundaries (center +/- half-width/height)
        left = x_center - width / 2
        right = x_center + width / 2
        top = y_center - height / 2
        bottom = y_center + height / 2

        if left < 0:
            return False, f"Box extends past left boundary: x_center={x_center}, width={width}"

        if right > 1:
            return False, f"Box extends past right boundary: x_center={x_center}, width={width}"

        if top < 0:
            return False, f"Box extends past top boundary: y_center={y_center}, height={height}"

        if bottom > 1:
            return False, f"Box extends past bottom boundary: y_center={y_center}, height={height}"

        # Check dimensions are positive
        if width <= 0 or height <= 0:
            return False, f"Dimensions must be positive: {width}x{height}"

        return True, "Valid"

    except Exception as e:
        return False, f"Validation error: {e}"


class ValidationReporter:
    """Generate validation reports"""

    @staticmethod
    def format_report(stats: dict) -> str:
        """Format validation statistics as readable report"""

        report = []
        report.append("=" * 70)
        report.append("PSEUDO-LABEL VALIDATION REPORT")
        report.append("=" * 70)

        report.append("\nIMPORTANT NOTES:")
        report.append("  - GEOMETRIC validation: Box coordinates and dimensions are valid")
        report.append("  - SEMANTIC validation: NOT PERFORMED")
        report.append("  - Passing geometric validation does NOT prove box identifies correct field")
        report.append("  - Forged-field proposals marked as UNRELIABLE and unverified")
        report.append("  - Alignment-uncertain proposals have reduced confidence")

        report.append("\n" + "=" * 70)
        report.append("PROPOSAL GENERATION INPUT")
        report.append("=" * 70)

        if 'input' in stats:
            for key, val in stats['input'].items():
                report.append(f"{key:40}: {val}")

        report.append("\n" + "=" * 70)
        report.append("TEMPLATE-BASED PROPOSALS")
        report.append("=" * 70)

        template = stats.get('template_proposals', {})
        successful = template.get('successful', 0)
        failed = template.get('failed', 0)
        report.append(f"Successfully generated:          {successful}")
        report.append(f"Failed:                          {failed}")

        if template.get('reasons'):
            report.append("\nFailure reasons:")
            for reason, count in sorted(template['reasons'].items()):
                report.append(f"  {reason:40}: {count}")

        report.append("\n" + "=" * 70)
        report.append("OCR-BASED PROPOSALS")
        report.append("=" * 70)

        ocr = stats.get('ocr_proposals', {})
        report.append(f"Successfully generated:          {ocr.get('successful', 0)}")
        report.append(f"Failed:                          {ocr.get('failed', 0)}")
        report.append(f"Text regions extracted:          {ocr.get('text_regions', 0)}")

        report.append("\n" + "=" * 70)
        report.append("PROPOSAL FUSION (Template + OCR)")
        report.append("=" * 70)

        fusion = stats.get('fusion', {})
        report.append(f"Using both methods:              {fusion.get('both_methods', 0)}")
        report.append(f"Using template only:             {fusion.get('template_only', 0)}")
        report.append(f"Using OCR only:                  {fusion.get('ocr_only', 0)}")
        report.append(f"Using neither (no proposal):     {fusion.get('neither', 0)}")

        report.append("\n" + "=" * 70)
        report.append("VARIANT PROPAGATION")
        report.append("=" * 70)

        prop = stats.get('propagation', {})
        report.append(f"Successfully propagated:         {prop.get('successful', 0)}")
        report.append(f"Alignment uncertain (flagged):   {prop.get('alignment_uncertain', 0)}")
        report.append(f"Failed:                          {prop.get('failed', 0)}")

        report.append("\nNOTE: Alignment-uncertain proposals are flagged with reduced confidence.")
        report.append("They are usable but should be treated cautiously.")

        report.append("\n" + "=" * 70)
        report.append("BOUNDING BOX VALIDATION (GEOMETRIC)")
        report.append("=" * 70)

        val = stats.get('validation', {})
        valid_boxes = val.get('boxes_valid', 0)
        invalid_boxes = val.get('boxes_invalid', 0)
        total_boxes = valid_boxes + invalid_boxes

        report.append(f"Total boxes generated:           {total_boxes}")
        report.append(f"Valid boxes:                     {valid_boxes}")
        report.append(f"Invalid boxes:                   {invalid_boxes}")

        if invalid_boxes > 0 and val.get('invalid_reasons'):
            report.append("\nInvalid box reasons:")
            for reason, count in sorted(val['invalid_reasons'].items()):
                report.append(f"  {reason:40}: {count}")

        report.append("\n" + "=" * 70)
        report.append("YOLO LABEL VALIDATION (GEOMETRIC)")
        report.append("=" * 70)

        yolo_valid = val.get('yolo_valid', 0)
        yolo_invalid = val.get('yolo_invalid', 0)
        total_yolo = yolo_valid + yolo_invalid

        report.append(f"Total YOLO labels generated:     {total_yolo}")
        report.append(f"Valid YOLO labels:               {yolo_valid}")
        report.append(f"Invalid YOLO labels:             {yolo_invalid}")

        report.append("\n" + "=" * 70)
        report.append("PER-FIELD COVERAGE")
        report.append("=" * 70)

        total_images = stats.get('input', {}).get('total_approved_images', 315)
        coverage = stats.get('per_field_coverage', {})

        field_names = [
            'cheque_number', 'bank_name', 'account_number', 'date',
            'payee_name', 'amount', 'signature', 'micr_code'
        ]

        for field_name in field_names:
            count = coverage.get(field_name, 0)
            pct = (count / total_images * 100) if total_images > 0 else 0
            report.append(f"{field_name:25}: {count:3}/{total_images} ({pct:5.1f}%)")

        report.append("\n" + "=" * 70)
        report.append("IMPORTANT REMINDERS")
        report.append("=" * 70)
        report.append("\n1. GEOMETRIC vs SEMANTIC Validation:")
        report.append("   - Geometric: coordinates are valid, box doesn't overflow")
        report.append("   - Semantic: box identifies the correct field (NOT CHECKED)")
        report.append("   - Valid geometric ≠ correct field assignment")

        report.append("\n2. Forged Field Proposals:")
        report.append("   - Marked as UNRELIABLE (confidence=0.15)")
        report.append("   - Should NOT be used for training")
        report.append("   - Flagged with: 'forged_field_flag': true")

        report.append("\n3. Alignment-Uncertain Proposals:")
        report.append("   - Variant images with layout mismatches")
        report.append("   - Confidence reduced by 0.3")
        report.append("   - Flagged with: 'alignment_check': {...}")

        report.append("\n4. Next Steps:")
        report.append("   - Review metadata.json for proposal details")
        report.append("   - Inspect OCR evidence (recorded in each proposal)")
        report.append("   - Manually validate sample proposals")
        report.append("   - Decide on confidence threshold for training")
        report.append("   - DO NOT train until results reviewed and approved")

        report.append("\n" + "=" * 70)

        return "\n".join(report)
