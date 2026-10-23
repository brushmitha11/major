"""
Phase 3 Field Localization — Bank-Specific Templates

IMPORTANT: All field coordinates are PROVISIONAL PLACEHOLDER ESTIMATES derived from manual
visual inspection of TRAIN split samples only. They are NOT validated against ground-truth
bounding-box annotations. Coordinates are INDEPENDENTLY estimated per bank and subject to
significant refinement once proper annotations are collected.

CANONICAL COORDINATE SYSTEM: The template uses a provisional canonical coordinate space
of 2365 × 1080 pixels. This is NOT the actual physical pixel size of cheques (which vary).
The registration stage maps this canonical template space to each input image's actual
coordinates via affine transformation.

BANK-SPECIFIC COORDINATES: Each bank template has independently estimated field positions.
Do NOT assume that banks share identical field layouts. Current placeholder values are
provisional diagnostic estimates only.

Status: All templates marked as 'placeholder_estimate'. Do NOT present these as validated
or comparable across banks until proper per-bank ground-truth annotations are available.
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional


@dataclass
class FieldDefinition:
    """Single field region definition"""
    name: str
    bbox_canonical: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    field_type: str  # 'text', 'handwritten', 'signature'
    applicability: List[str]  # list of banks where applicable
    status: str  # 'placeholder_estimate'
    description: str


class ChequeTemplate:
    """Base class for bank-specific cheque templates"""

    def __init__(self, bank_name: str, fields: Dict[str, FieldDefinition]):
        self.bank_name = bank_name
        self.fields = fields
        # Provisional canonical coordinate space (NOT actual image pixel size)
        # Registration maps this to actual input image coordinates
        self.canonical_width = 2365
        self.canonical_height = 1080
        self.canonical_corners = (
            (0, 0),                                    # top-left
            (self.canonical_width, 0),                 # top-right
            (self.canonical_width, self.canonical_height),  # bottom-right
            (0, self.canonical_height),                # bottom-left
        )

    def get_field(self, field_name: str) -> Optional[FieldDefinition]:
        """Get field definition by name"""
        if field_name not in self.fields:
            return None
        return self.fields[field_name]

    def get_all_fields(self) -> List[FieldDefinition]:
        """Get all field definitions"""
        return list(self.fields.values())

    def get_applicable_fields(self) -> List[FieldDefinition]:
        """Get fields applicable to this bank"""
        return [f for f in self.fields.values() if self.bank_name in f.applicability]


class AxisTemplate(ChequeTemplate):
    """AXIS BANK cheque template (PROVISIONAL PLACEHOLDER ESTIMATES - TRAIN DATA ONLY)

    Coordinates are independently estimated for AXIS BANK.
    Do NOT assume identical layout to other banks.
    Subject to refinement once proper AXIS-specific annotations are available.
    """

    def __init__(self):
        fields = {
            'amount': FieldDefinition(
                name='amount',
                bbox_canonical=(2100, 350, 2300, 400),
                field_type='text',
                applicability=['AXIS BANK'],
                status='placeholder_estimate',
                description='[AXIS] Rupee amount field (provisional estimate)'
            ),
            'payee': FieldDefinition(
                name='payee',
                bbox_canonical=(400, 180, 1000, 220),
                field_type='text',
                applicability=['AXIS BANK'],
                status='placeholder_estimate',
                description='[AXIS] Payee name field (provisional estimate)'
            ),
            'signature': FieldDefinition(
                name='signature',
                bbox_canonical=(1800, 850, 1950, 930),
                field_type='handwritten',
                applicability=['AXIS BANK'],
                status='placeholder_estimate',
                description='[AXIS] Signature area (provisional estimate)'
            ),
        }
        super().__init__('AXIS BANK', fields)


class CanaraTemplate(ChequeTemplate):
    """CANARA BANK cheque template (PROVISIONAL PLACEHOLDER ESTIMATES - TRAIN DATA ONLY)

    Coordinates are independently estimated for CANARA BANK.
    Do NOT assume identical layout to other banks.
    Subject to refinement once proper CANARA-specific annotations are available.
    """

    def __init__(self):
        fields = {
            'amount': FieldDefinition(
                name='amount',
                bbox_canonical=(2100, 350, 2300, 400),
                field_type='text',
                applicability=['CANARA BANK'],
                status='placeholder_estimate',
                description='[CANARA] Rupee amount field (provisional estimate)'
            ),
            'payee': FieldDefinition(
                name='payee',
                bbox_canonical=(400, 180, 1000, 220),
                field_type='text',
                applicability=['CANARA BANK'],
                status='placeholder_estimate',
                description='[CANARA] Payee name field (provisional estimate)'
            ),
            'signature': FieldDefinition(
                name='signature',
                bbox_canonical=(1800, 850, 1950, 930),
                field_type='handwritten',
                applicability=['CANARA BANK'],
                status='placeholder_estimate',
                description='[CANARA] Signature area (provisional estimate)'
            ),
        }
        super().__init__('CANARA BANK', fields)


class IciciTemplate(ChequeTemplate):
    """ICICI BANK cheque template (PROVISIONAL PLACEHOLDER ESTIMATES - TRAIN DATA ONLY)

    Coordinates are independently estimated for ICICI BANK.
    Do NOT assume identical layout to other banks.
    Subject to refinement once proper ICICI-specific annotations are available.
    """

    def __init__(self):
        fields = {
            'amount': FieldDefinition(
                name='amount',
                bbox_canonical=(2100, 350, 2300, 400),
                field_type='text',
                applicability=['ICICI BANK'],
                status='placeholder_estimate',
                description='[ICICI] Rupee amount field (provisional estimate)'
            ),
            'payee': FieldDefinition(
                name='payee',
                bbox_canonical=(400, 180, 1000, 220),
                field_type='text',
                applicability=['ICICI BANK'],
                status='placeholder_estimate',
                description='[ICICI] Payee name field (provisional estimate)'
            ),
            'date': FieldDefinition(
                name='date',
                bbox_canonical=(1950, 100, 2070, 130),
                field_type='text',
                applicability=['ICICI BANK'],
                status='placeholder_estimate',
                description='[ICICI ONLY] Date field (provisional estimate - ICICI only in V1)'
            ),
            'signature': FieldDefinition(
                name='signature',
                bbox_canonical=(1800, 850, 1950, 930),
                field_type='handwritten',
                applicability=['ICICI BANK'],
                status='placeholder_estimate',
                description='[ICICI] Signature area (provisional estimate)'
            ),
        }
        super().__init__('ICICI BANK', fields)


class SyndicateTemplate(ChequeTemplate):
    """SYNDICATE BANK cheque template (PROVISIONAL PLACEHOLDER ESTIMATES - TRAIN DATA ONLY)

    Coordinates are independently estimated for SYNDICATE BANK.
    Do NOT assume identical layout to other banks.
    Subject to refinement once proper SYNDICATE-specific annotations are available.
    """

    def __init__(self):
        fields = {
            'amount': FieldDefinition(
                name='amount',
                bbox_canonical=(2100, 350, 2300, 400),
                field_type='text',
                applicability=['SYNDICATE BANK'],
                status='placeholder_estimate',
                description='[SYNDICATE] Rupee amount field (provisional estimate)'
            ),
            'payee': FieldDefinition(
                name='payee',
                bbox_canonical=(400, 180, 1000, 220),
                field_type='text',
                applicability=['SYNDICATE BANK'],
                status='placeholder_estimate',
                description='[SYNDICATE] Payee name field (provisional estimate)'
            ),
            'signature': FieldDefinition(
                name='signature',
                bbox_canonical=(1800, 850, 1950, 930),
                field_type='handwritten',
                applicability=['SYNDICATE BANK'],
                status='placeholder_estimate',
                description='[SYNDICATE] Signature area (provisional estimate)'
            ),
        }
        super().__init__('SYNDICATE BANK', fields)


# Template registry — TRAIN data only for development
TEMPLATE_REGISTRY = {
    'AXIS BANK': AxisTemplate(),
    'CANARA BANK': CanaraTemplate(),
    'ICICI BANK': IciciTemplate(),
    'SYNDICATE BANK': SyndicateTemplate(),
}


def get_template(bank: str) -> Optional[ChequeTemplate]:
    """Get template for a bank. Returns None if bank is unknown."""
    return TEMPLATE_REGISTRY.get(bank, None)
