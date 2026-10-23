# Automated Pseudo-Label Generation Pipeline (REVISED)
## Conservative, Evidence-Based Approach

**Status**: PROPOSAL (REVISED FOR APPROVAL)  
**Scope**: Proposal generation ONLY - no training, no model installation  
**Key Change**: All estimates marked as unverified; actual results reported only

---

## Executive Summary

This pipeline will:
1. Generate **candidate bounding boxes** for all 315 approved training images from train.csv
2. **Validate every proposal** - check coordinates, class IDs, image alignment
3. **Record evidence** - save OCR text, method source, confidence basis
4. **Measure actual results** - report numbers generated, failures, uncertainties (no estimates)
5. **Preserve data integrity** - separate pseudo-labels from verified annotations, don't modify any source files
6. **Stop after generation** - results reviewed before any training

---

## Corrected Workflow

### Phase 1: Proposal Generation with Validation

#### Step 1.1: Template-Based Proposals (Existing Code)
**Input**: ChequeFieldExtractorV2 field definitions  
**Process**:
- For each of 315 approved images from train.csv:
  - Extract template region (normalized coordinates)
  - Detect content via edge detection + contrast analysis
  - Save: `{field: {box, method: "template", confidence_basis: "edge_density_0.X"}}`

**Output**: Template proposals (incomplete - some fields may have 0 confidence)  
**Validation**: 
- All boxes must have 0 ≤ x_min < x_max ≤ 1 and 0 ≤ y_min < y_max ≤ 1
- Box dimensions (x_max - x_min) and (y_max - y_min) must be > 0.01

#### Step 1.2: OCR-Based Proposals (NEW - WITH EVIDENCE RECORDING)
**Input**: Raw image, no pattern assumptions  
**Process**:
```
For each image:
  1. Run EasyOCR → returns [(text, bbox, confidence), ...]
  2. For each detected text region:
     a. Record: text content, bbox, ocr_confidence, character_certainties
     b. Store as raw evidence (not yet classified)
  3. Attempt field classification:
     a. IF text matches cheque number pattern (6-10 digits):
        - Assign to cheque_number field
        - Record: "Matched pattern: 6-10 consecutive digits"
        - Confidence = ocr_confidence
     b. IF text matches date pattern (d/d/yyyy):
        - Assign to date field
        - Record: "Matched pattern: date format"
     c. IF text matches numeric amount (digits, commas, decimals):
        - Potential amount field
        - Record: "Numeric content detected, position suggests amount region"
     d. IF large text cluster in center region:
        - Potential payee_name field
        - Record: "Text cluster in center region, likely payee"
     e. IF text matches 9-digit MICR pattern:
        - Assign to micr_code
        - Record: "Matched MICR pattern: 9 digits"
     f. ELSE:
        - Store as unclassified evidence
        - Record: "Detected text but no field match: <text>"
  4. Output per-field:
     {field: {
       box: <normalized_coords>,
       method: "ocr",
       ocr_text: "<actual_extracted_text>",
       ocr_confidence: 0.X,
       evidence: "<reasoning for field assignment>",
       classification_confidence: "high|medium|low"
     }}
```

**Key constraint**: Do NOT assume field based on position alone. Require pattern or structural match.

**Output**: OCR proposals with full evidence trail  
**Validation**:
- All boxes have normalized coordinates in [0, 1]
- All boxes have positive dimensions > 0.01
- OCR text recorded (for manual inspection if needed)
- Evidence field explains classification reasoning

#### Step 1.3: Proposal Fusion
**Input**: Template proposals + OCR proposals for same image  
**Process**:
```
For each field:
  IF template confidence > 0.5 AND ocr confidence > 0.5:
    # Both methods agree
    fused_box = average(template_box, ocr_box)
    fused_confidence = avg(template_conf, ocr_conf)
    method_sources = ["template", "ocr"]
  ELSE IF template confidence > ocr confidence:
    fused_box = template_box
    fused_confidence = template_confidence
    method_sources = ["template"]
  ELSE IF ocr confidence > 0.7:
    fused_box = ocr_box
    fused_confidence = ocr_confidence
    method_sources = ["ocr"]
  ELSE:
    # Neither method confident
    fused_box = template_box  # Default fallback
    fused_confidence = 0.3    # Low confidence marker
    method_sources = ["template_fallback"]
    note = "Low confidence - manual review recommended"
```

**Output**: Single proposal per field with method source traceback

#### Step 1.4: Variant Propagation WITH VALIDATION
**Input**: Reference image proposals + train.csv metadata  
**Process**:
```
For each variant image in train.csv:
  1. Look up parent_id and forgery_type from train.csv
  2. Load parent reference image proposals
  3. VALIDATION STEP - Check image alignment:
     a. Load parent image, load variant image
     b. Compare dimensions (width, height)
     c. If dimensions differ significantly (>5%):
        - Flag as "alignment_uncertain"
        - Reduce confidence by 0.3 for all propagated fields
        - Record: "Variant dimensions differ from parent by X%"
     d. If dimensions match (within 5%):
        - Proceed with confidence inheritance
  4. For each field:
     IF forgery_type indicates this field was forged:
        confidence = 0.15  # Very low - likely corrupted
        note = "FORGED: Field was modified in this variant"
        is_reliable = false
     ELSE:
        confidence = parent_confidence  # Inherit parent
        note = "Propagated from parent image"
        is_reliable = true
  5. Output variant proposal with propagation metadata
```

**Output**: All 315 image proposals (78 reference + 237 validated variants)  
**Validation**: 
- Check dimension alignment before propagation
- Flag uncertain cases explicitly
- Never override parent confidence without dimension check

---

### Phase 2: Comprehensive Validation

#### Validation 2.1: Bounding Box Validation
**For every generated proposal**:
```python
def validate_box(box, image_path, field_name):
    x_min, y_min, width, height = box
    
    # Check coordinates are normalized [0,1]
    assert 0 <= x_min < 1 and 0 <= y_min < 1, f"Invalid min coords for {field}"
    assert 0 < width <= 1 and 0 < height <= 1, f"Invalid dimensions for {field}"
    
    # Check box doesn't overflow
    assert x_min + width <= 1, f"Box extends past right edge"
    assert y_min + height <= 1, f"Box extends past bottom edge"
    
    # Check minimum size (avoid tiny/degenerate boxes)
    assert width > 0.01 and height > 0.01, f"Box too small: {width}x{height}"
    
    # Check maximum size (avoid entire image)
    assert width < 0.95 and height < 0.95, f"Box too large: {width}x{height}"
    
    return True
```

**Output**: 
- Valid boxes: saved to proposals
- Invalid boxes: logged and rejected, field marked as "generation_failed"

#### Validation 2.2: YOLO Label Validation
**For every YOLO format label generated**:
```python
def validate_yolo_label(class_id, x_center, y_center, width, height):
    
    # Check class ID
    assert 0 <= class_id <= 7, f"Invalid class ID: {class_id}"
    
    # Check normalized coordinates
    assert 0 <= x_center <= 1, f"x_center out of range: {x_center}"
    assert 0 <= y_center <= 1, f"y_center out of range: {y_center}"
    assert 0 < width <= 1, f"width invalid: {width}"
    assert 0 < height <= 1, f"height invalid: {height}"
    
    # Check box doesn't extend past boundaries
    assert x_center - width/2 >= 0, f"Box extends past left"
    assert x_center + width/2 <= 1, f"Box extends past right"
    assert y_center - height/2 >= 0, f"Box extends past top"
    assert y_center + height/2 <= 1, f"Box extends past bottom"
    
    return True
```

**Output**:
- Valid YOLO labels: saved
- Invalid labels: logged, counted as generation failure

#### Validation 2.3: Image Path Validation
**For every image in proposals**:
```python
def validate_image_exists(image_path, train_csv_path):
    # Check image is in approved train.csv
    assert image_path in train_csv_entries, f"Not in train.csv: {image_path}"
    
    # Check image file exists on disk
    full_path = PROJECT_ROOT / image_path
    assert full_path.exists(), f"File not found: {full_path}"
    
    # Check file is readable
    assert os.access(full_path, os.R_OK), f"File not readable: {full_path}"
    
    return True
```

**Output**: Only images in train.csv are processed; all others skipped with log entry

---

### Phase 3: Results Reporting

**After generation complete, report ACTUAL numbers**:

```
PSEUDO-LABEL GENERATION RESULTS
================================

INPUT:
  Total approved images (train.csv): 315
    - Reference images: 78
    - Variant images: 237

TEMPLATE-BASED PROPOSALS:
  Successfully generated: XXX / 315
  Failed: YYY
  Reasons for failure:
    - Low content detection: ZZZ images
    - Invalid coordinates: AAA images

OCR-BASED PROPOSALS:
  Successfully extracted text from: XXX / 315
  Failed OCR (image too blurry/low contrast): YYY
  Text regions classified as fields:
    - cheque_number: AAA images
    - amount: BBB images
    - date: CCC images
    - payee_name: DDD images
    - bank_name: EEE images
    - account_number: FFF images
    - micr_code: GGG images
    - signature: HHH images
    - unclassified: III regions (stored as evidence)

FUSED PROPOSALS:
  Successfully created: XXX / 315
  Proposals using both methods: AAA
  Proposals using template only: BBB
  Proposals using OCR only: CCC

VARIANT PROPAGATION:
  Successfully propagated: XXX / 237
  Failed (dimension mismatch): YYY
    - Images flagged as alignment_uncertain: ZZZ
    - Confidence reduced by 0.3 for these cases
  Propagated with forged field flags: XXX (confidence=0.15)

VALIDATION RESULTS:

Bounding Box Validation:
  Total boxes generated: NNN
  Valid boxes: AAA (passed all checks)
  Invalid boxes: BBB (rejected)
    - Coordinates out of range: CCC
    - Box too small: DDD
    - Box extends past image: EEE

YOLO Label Validation:
  Total YOLO labels generated: NNN
  Valid labels: AAA
  Invalid labels: BBB
  Class distribution:
    - Class 0 (cheque_number): CCC
    - Class 1 (bank_name): DDD
    - Class 2 (account_number): EEE
    - Class 3 (date): FFF
    - Class 4 (payee_name): GGG
    - Class 5 (amount): HHH
    - Class 6 (signature): III
    - Class 7 (micr_code): JJJ

FINAL PSEUDO-LABEL STATISTICS:

Per-field coverage:
  cheque_number: XXX / 315 proposals (XX%)
  bank_name: XXX / 315 proposals (XX%)
  account_number: XXX / 315 proposals (XX%)
  date: XXX / 315 proposals (XX%)
  payee_name: XXX / 315 proposals (XX%)
  amount: XXX / 315 proposals (XX%)
  signature: XXX / 315 proposals (XX%)
  micr_code: XXX / 315 proposals (XX%)

Average confidence by field:
  cheque_number: X.XX
  bank_name: X.XX
  account_number: X.XX
  date: X.XX
  payee_name: X.XX
  amount: X.XX
  signature: X.XX
  micr_code: X.XX

OCR Evidence Summary:
  OCR text recorded for: XXX proposals
  Evidence traces available: YYY proposals
  Evidence traces missing: ZZZ proposals

PSEUDO-LABELS STORAGE:

Files created:
  ✓ phase3/data/pseudo_labels/metadata.json (315 images)
    - Each entry marked is_verified: false
    - Method sources recorded
    - OCR text saved
    - Evidence trails included
  
  ✓ phase3/data/pseudo_labels/yolo/train/*.txt (valid labels only)
    - XXX files created (one per image with valid labels)
    - YYY images skipped (no valid proposals)
    - All labels validated before export
  
  ✓ phase3/data/pseudo_labels/validation_report.json
    - Detailed validation results
    - Failed proposals listed
    - Reasons for failures documented

DATA INTEGRITY:

Modified files: NONE
  - No changes to datasets/splits/train.csv ✓
  - No changes to original images ✓
  - No changes to verified annotations ✓
  - No packages installed ✓

New files (isolated):
  - All in phase3/data/pseudo_labels/ (separate from verified data)
  - Marked as unverified pseudo-labels
  - Can be deleted/regenerated without impact

NEXT STEPS FOR REVIEW:

1. Review metadata.json for proposal quality
2. Inspect validation_report.json for failure reasons
3. Check OCR evidence for low-confidence proposals
4. Examine YOLO labels (random sample):
   - Verify class IDs match field assignments
   - Check coordinate ranges are valid
   - Compare visual boxes to image content
5. Decide: proceed with quality sampling? Or refine generation first?

NOTE: All numbers above are ACTUAL measured results from generation.
No estimates or projections included.
```

---

## Implementation Files (CORRECTED)

### Files to CREATE (4 files)

#### 1. `phase3/ocr_proposal_generator.py` (250-300 lines)
**Changes from original plan**:
- Record all OCR text and evidence
- Don't assume field from position - require pattern match or explicit evidence
- Save classification_confidence (high/medium/low, not just numeric)
- Skip invalid boxes rather than forcing them

#### 2. `phase3/variant_propagation_manager.py` (200-250 lines)
**Changes from original plan**:
- ADD: Image dimension comparison before propagation
- ADD: Flag uncertain cases explicitly
- CHANGE: Reduce confidence for dimension mismatches, don't fail
- RECORD: Propagation metadata (parent_id, dimension_check_result, forgery_type)

#### 3. `phase3/pseudo_label_pipeline.py` (400-500 lines)
**Changes from original plan**:
- ADD: Comprehensive validation for every box
- ADD: Detailed logging of all failures with reasons
- ADD: Evidence recording (OCR text, method sources, confidence bases)
- ADD: Statistics reporting (actual counts)
- CHANGE: No quality estimation - only actual measured results
- CHANGE: Results are REPORTED, not analyzed for pass/fail

#### 4. `phase3/pseudo_label_validator.py` (150-200 lines)
**NEW file - validation logic**:
- `validate_box()` - check normalized coordinates and dimensions
- `validate_yolo_label()` - check YOLO format compliance
- `validate_image_exists()` - check image in train.csv and on disk
- `generate_validation_report()` - detailed failure reasons

### Files to MODIFY

#### 1. `phase3/.gitignore`
**Add**:
```
phase3/data/pseudo_labels/metadata.json
phase3/data/pseudo_labels/validation_report.json
phase3/data/pseudo_labels/yolo/
```

#### 2. `phase3/annotation_ui_backend.py` (Optional, can skip for now)
**If added**:
- Route: `GET /api/pseudo_labels/<uid>` (returns proposals marked as unverified)
- Route: `GET /api/validation_report` (returns validation results)
- NOTE: Don't add until proposals reviewed

#### 3. `phase3/annotation_ui.html` (Optional, can skip for now)
**If added**:
- Toggle to display pseudo-labels (marked distinctly as unverified)
- NOTE: Don't add until proposals reviewed

---

## Key Corrections Made

| Original Plan | Issue | Correction |
|---------------|-------|-----------|
| Estimated 75% accuracy | Unverified | Report actual numbers only |
| Pattern matching alone | Too loose | Require evidence + record OCR text |
| Assume variant alignment | May fail | Validate dimensions, flag uncertain |
| Confidence scores only | Opaque | Record evidence, method sources, OCR text |
| Quality estimation sample | Unverified | Stop after generation, report for manual review |
| No validation | Risky | Comprehensive validation on every box/label |
| No failure reporting | Hidden problems | Detailed failure reasons and counts |
| Auto-classified fields | Unreliable | Classification confidence marked, OCR text saved |

---

## Actual Execution

### Step 1: Generate Proposals (Automated, ~5-10 min)
```python
from pseudo_label_pipeline import PseudoLabelPipeline
from pseudo_label_validator import ValidationReporter

pipeline = PseudoLabelPipeline(
    train_csv_path="datasets/splits/train.csv",
    output_dir="data/pseudo_labels"
)

# Generate with full validation
proposals = pipeline.generate_all_proposals_with_validation()

# Report actual results
reporter = ValidationReporter(proposals)
report = reporter.generate_report()

print(report)  # Print actual numbers to console
report.save("data/pseudo_labels/validation_report.json")

# Save metadata (marked as unverified)
pipeline.save_metadata(proposals, mark_verified=False)

# Export YOLO (only valid boxes)
pipeline.export_yolo_format_validated(proposals)
```

### Output Files
```
phase3/data/pseudo_labels/
├── metadata.json (315 entries, all marked is_verified: false)
├── validation_report.json (detailed results)
└── yolo/train/
    └── *.txt (only for images with valid proposals)
```

### Step 2: STOP AND REVIEW
Print validation_report.json. Review for:
- How many proposals generated per field?
- What validation failures occurred?
- Are OCR text and evidence recorded?
- Are forged fields flagged with low confidence?

DO NOT PROCEED TO TRAINING YET.

---

## What Will NOT Happen

- ✗ No model training
- ✗ No package installation (EasyOCR already available)
- ✗ No modification of train.csv or splits
- ✗ No modification of original images
- ✗ No modification of verified annotations
- ✗ No automatic quality estimation
- ✗ No estimated accuracies reported as facts
- ✗ No test/validation data touched

---

## What WILL Be Reported

- ✓ Actual number of proposals generated (per field, per method)
- ✓ Actual number of failures (with specific reasons)
- ✓ Validation results (boxes, YOLO labels)
- ✓ OCR text and evidence for each proposal
- ✓ Confidence scores (with basis explained)
- ✓ Forged field flags (confidence=0.15)
- ✓ Dimension mismatch flags (for variants)
- ✓ Coverage statistics (proposals per field)

---

## Approval Checklist

- [ ] Evidence recording approach acceptable? (OCR text + reasoning)
- [ ] Dimension validation before propagation acceptable?
- [ ] Confidence scoring approach (with basis explanation) acceptable?
- [ ] Validation criteria (box size, coordinate ranges, YOLO format) acceptable?
- [ ] Results reporting structure (actual numbers, no estimates) acceptable?
- [ ] OK to implement only proposal generation, stop before training?
- [ ] Ready to proceed?

