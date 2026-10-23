# Implementation Checklist: Automated Pseudo-Label Pipeline (REVISED)

**Status**: AWAITING APPROVAL  
**Key Change**: All estimates removed, actual measurement-based approach

---

## Files to CREATE (4 New Files)

### 1. `phase3/ocr_proposal_generator.py` (~250-300 lines)
**Purpose**: Generate proposals using EasyOCR with full evidence recording

**Key Functions**:
- `OCRProposalGenerator.__init__()`
  - Initialize EasyOCR reader
  - Log initialization success/failure

- `OCRProposalGenerator.extract_text_regions(image_path) → list`
  - Input: image file path
  - Returns: [(text, bbox, confidence), ...] from EasyOCR
  - Handles failures: log error, return empty list

- `OCRProposalGenerator.classify_text_to_field(text, bbox, position) → (field_name, evidence, confidence)`
  - Input: OCR text, bounding box, position in image
  - Returns: (field_assignment, reasoning_string, confidence_level)
  - Logic:
    ```
    IF text matches 6-10 consecutive digits AND (position right-side OR small region):
      field = "cheque_number"
      evidence = f"Matched pattern: 6-10 digits. Text: {text}"
      confidence = "high"
    ELIF text matches date pattern (d/d/yyyy) AND (position right-side):
      field = "date"
      evidence = f"Matched date format. Text: {text}"
      confidence = "high"
    ELIF text matches numeric (digits/commas/decimals) AND (position right-side) AND amount-sized:
      field = "amount"
      evidence = f"Numeric content in expected amount region. Text: {text}"
      confidence = "medium"
    ELIF text is 9-digit number AND (position bottom):
      field = "micr_code"
      evidence = f"Matched MICR pattern: 9 digits. Text: {text}"
      confidence = "high"
    ELIF large text cluster in center region:
      field = "payee_name"
      evidence = f"Text cluster in center region (typical payee position)"
      confidence = "medium"
    ELIF text in top-left region AND short:
      field = "bank_name"
      evidence = f"Text in top-left region (typical bank position)"
      confidence = "medium"
    ELIF text in left region AND 8-20 digits:
      field = "account_number"
      evidence = f"Numeric content (8-20 digits) in left region. Text: {text}"
      confidence = "low"
    ELSE:
      field = None
      evidence = f"No field classification. Text: {text}"
      confidence = None
    ```
  - **IMPORTANT**: Don't assign based on position alone. Position + pattern/structure.

- `OCRProposalGenerator.generate_proposals(image_path) → dict`
  - Input: image path
  - Process:
    1. Extract text regions via EasyOCR
    2. For each region, classify to field
    3. Build proposal per field (taking highest confidence assignment)
    4. Record OCR text and evidence for tracing
  - Returns:
    ```
    {
      "cheque_number": {
        "box": [x_min, y_min, width, height],  # normalized
        "method": "ocr",
        "ocr_text": "309137",
        "ocr_confidence": 0.95,
        "evidence": "Matched pattern: 6-10 digits. Text: 309137",
        "classification_confidence": "high"
      },
      "payee_name": {
        "box": [...],
        "method": "ocr",
        "ocr_text": "John Doe",
        "ocr_confidence": 0.87,
        "evidence": "Text cluster in center region",
        "classification_confidence": "medium"
      },
      "_unclassified_text": [
        {"text": "some text", "bbox": [...], "ocr_confidence": 0.75, "reason": "No field match"}
      ]
    }
    ```
  - **Log all steps**: text found, classifications attempted, fields assigned

**Error Handling**:
- If EasyOCR fails: log error, return empty proposals dict
- If image path invalid: log, skip image
- Invalid coordinates from OCR: log warning, skip that region

---

### 2. `phase3/variant_propagation_manager.py` (~200-250 lines)
**Purpose**: Propagate proposals from parent to variants with dimension validation

**Key Functions**:
- `VariantPropagationManager.__init__(train_csv_path)`
  - Load train.csv
  - Build parent→variant mapping from metadata

- `VariantPropagationManager.load_parent_proposals(parent_id) → dict`
  - Load proposals for reference image
  - Returns: same format as OCR proposals

- `VariantPropagationManager.validate_image_alignment(parent_image_path, variant_image_path) → tuple`
  - Load both images
  - Compare dimensions (width, height)
  - Returns: (is_aligned, dimension_diff_percent, notes)
  - Logic:
    ```
    parent_w, parent_h = load_image(parent_path).shape
    variant_w, variant_h = load_image(variant_path).shape
    
    diff_w = abs(parent_w - variant_w) / parent_w * 100
    diff_h = abs(parent_h - variant_h) / parent_h * 100
    
    if diff_w > 5% or diff_h > 5%:
      return (False, max(diff_w, diff_h), f"Width diff: {diff_w}%, Height diff: {diff_h}%")
    else:
      return (True, max(diff_w, diff_h), "Dimensions match within 5%")
    ```

- `VariantPropagationManager.propagate_to_variant(parent_proposals, forgery_type, alignment_check) → dict`
  - Input: parent proposals, forgery_type (from train.csv), alignment validation result
  - Process:
    ```
    propagated_proposals = {}
    
    for field in parent_proposals:
      parent_field = parent_proposals[field]
      
      # Check alignment
      if not alignment_check['is_aligned']:
        confidence_reduction = 0.3
        alignment_note = f"Alignment uncertain: {alignment_check['notes']}"
      else:
        confidence_reduction = 0
        alignment_note = None
      
      # Check if field was forged
      if forgery_type in ["amount_forgery"] and field == "amount":
        propagated_confidence = 0.15
        forged_note = "FORGED: Field was modified in this variant"
      elif forgery_type in ["payee_forgery"] and field == "payee_name":
        propagated_confidence = 0.15
        forged_note = "FORGED: Field was modified in this variant"
      elif forgery_type in ["multi_field_forgery"] and field in ["amount", "payee_name"]:
        propagated_confidence = 0.15
        forged_note = "FORGED: Field was modified in this variant"
      else:
        propagated_confidence = parent_field.get("confidence", 0.5) - confidence_reduction
        forged_note = None
      
      propagated_proposals[field] = {
        "box": parent_field["box"],
        "method": "propagated",
        "parent_id": parent_id,
        "parent_confidence": parent_field.get("confidence"),
        "propagated_confidence": propagated_confidence,
        "alignment_check": alignment_check,
        "forged_note": forged_note,
        "ocr_text": parent_field.get("ocr_text"),
        "evidence": f"Propagated from parent {parent_id}"
      }
    
    return propagated_proposals
    ```

- `VariantPropagationManager.process_all_variants(reference_proposals_dict, metadata) → dict`
  - Input: dict of {parent_id: proposals}, train.csv metadata
  - Process all 237 variants
  - For each variant:
    1. Get parent_id from metadata
    2. Get forgery_type from metadata
    3. Validate alignment
    4. Propagate with adjustments
  - Returns: {uid: propagated_proposals} for all variants

**Logging**:
- Log each variant's alignment check result
- Log confidence reductions for alignment mismatches
- Log forged field flags

---

### 3. `phase3/pseudo_label_pipeline.py` (~400-500 lines)
**Purpose**: Orchestrate entire proposal generation with validation and reporting

**Key Functions**:
- `PseudoLabelPipeline.__init__(train_csv_path, output_dir)`
  - Initialize all components
  - Set up logging

- `PseudoLabelPipeline.generate_template_proposals() → dict`
  - Use existing ChequeFieldExtractorV2
  - For each image in train.csv:
    1. Extract field region
    2. Detect content
    3. Save: {field: {box, method: "template", confidence: X, basis: "edge_density"}}
  - Log: total successful, failures

- `PseudoLabelPipeline.generate_ocr_proposals() → dict`
  - Use OCRProposalGenerator
  - For each image in train.csv:
    1. Call OCR proposal generator
    2. Collect proposals with evidence
  - Log: OCR success rate, classification success rate, unclassified text

- `PseudoLabelPipeline.fuse_proposals(template_dict, ocr_dict) → dict`
  - For each image, fuse template + OCR
  - Logic (already corrected above)
  - Log: proposals using both methods, using one method, using neither

- `PseudoLabelPipeline.propagate_variants(reference_proposals_dict) → dict`
  - Use VariantPropagationManager
  - Process all 237 variants
  - Log: successful propagations, alignment mismatches, forged field flags

- `PseudoLabelPipeline.generate_all_proposals_with_validation() → dict`
  - Call all steps above in sequence
  - Validate every proposal
  - Log comprehensive results

- `PseudoLabelPipeline.save_metadata(proposals_dict)`
  - Save to `phase3/data/pseudo_labels/metadata.json`
  - Format:
    ```json
    {
      "309137_reference": {
        "image_path": "datasets/raw/idrbt/300/Cheque 309137.tif",
        "label_source": "hybrid_proposal",
        "is_verified": false,
        "fields": {
          "cheque_number": {
            "box": [x, y, w, h],
            "methods_used": ["template", "ocr"],
            "confidence": 0.85,
            "confidence_basis": "averaged template(0.8) + ocr(0.9)",
            "ocr_text": "309137",
            "evidence": "Matched cheque number pattern"
          },
          ...
        }
      },
      "309137_amount_forgery": {
        "image_path": "datasets/synthetic/forged/axis/309137_amount_forgery.tif",
        "label_source": "variant_propagation",
        "is_verified": false,
        "parent_id": "309137",
        "forgery_type": "amount_forgery",
        "fields": {
          "amount": {
            "box": [...],
            "propagated_from": "309137_reference",
            "confidence": 0.15,
            "confidence_note": "FORGED - field was modified",
            "is_reliable": false
          },
          ...
        }
      }
    }
    ```
  - Mark every entry `is_verified: false`

- `PseudoLabelPipeline.export_yolo_format_validated(proposals_dict)`
  - For each image with valid proposals:
    1. Validate all boxes (coordinates, dimensions)
    2. Convert to YOLO format: class_id x_center y_center width height
    3. Write to `phase3/data/pseudo_labels/yolo/train/{uid}.txt`
  - Log: files created, skipped (no valid boxes)

---

### 4. `phase3/pseudo_label_validator.py` (~150-200 lines)
**Purpose**: Centralized validation logic and reporting

**Key Functions**:
- `validate_box(box_coords, min_size=0.01, max_size=0.95) → (is_valid, reason)`
  ```python
  x_min, y_min, width, height = box_coords
  
  if not (0 <= x_min < 1 and 0 <= y_min < 1):
    return False, "Min coordinates out of range"
  
  if not (0 < width <= 1 and 0 < height <= 1):
    return False, "Invalid dimensions"
  
  if x_min + width > 1 or y_min + height > 1:
    return False, "Box extends past image boundary"
  
  if width < min_size or height < min_size:
    return False, f"Box too small: {width}x{height}"
  
  if width > max_size or height > max_size:
    return False, f"Box too large: {width}x{height}"
  
  return True, "Valid"
  ```

- `validate_yolo_label(class_id, x_center, y_center, width, height) → (is_valid, reason)`
  ```python
  if not (0 <= class_id <= 7):
    return False, f"Invalid class ID: {class_id}"
  
  # Check coordinates are in [0, 1]
  for val in [x_center, y_center, width, height]:
    if not (0 <= val <= 1):
      return False, f"Coordinate out of range: {val}"
  
  # Check box doesn't overflow
  if x_center - width/2 < 0 or x_center + width/2 > 1:
    return False, "Box extends past left/right boundary"
  
  if y_center - height/2 < 0 or y_center + height/2 > 1:
    return False, "Box extends past top/bottom boundary"
  
  return True, "Valid"
  ```

- `ValidationReporter(proposals_dict, validation_results)`
  - Generate detailed report with actual numbers
  - Output format (as shown in REVISED_PLAN above)
  - Save to JSON

---

## Files to MODIFY

### 1. `phase3/.gitignore`
**Add**:
```
phase3/data/pseudo_labels/metadata.json
phase3/data/pseudo_labels/validation_report.json
phase3/data/pseudo_labels/yolo/train/
```

### 2. `phase3/annotation_ui_backend.py` (OPTIONAL - add later)
**If needed after proposal review**:
- Route: `GET /api/pseudo_labels/<uid>` 
- Route: `GET /api/validation_report`

### 3. `phase3/annotation_ui.html` (OPTIONAL - add later)
**If needed after proposal review**:
- Toggle: "Load Pseudo-Labels"
- Visual distinction (orange boxes, marked unverified)

---

## Output Files Expected

```
phase3/data/pseudo_labels/
├── metadata.json
│   └─ 315 entries, all marked is_verified: false
│   └─ OCR text recorded
│   └─ Evidence trails included
│   └─ Method sources documented
│
├── validation_report.json
│   └─ Actual counts (proposals, failures, reasons)
│   └─ Per-field coverage statistics
│   └─ Validation details (boxes, YOLO labels)
│   └─ Propagation results (successful, flagged, failed)
│
└── yolo/train/
    └─ *.txt (one per image with valid proposals)
    └─ YOLO format labels (class_id x y w h)
    └─ Only valid labels exported
```

---

## Execution Flow

### Step 1: Generate and Validate
```python
from pseudo_label_pipeline import PseudoLabelPipeline

pipeline = PseudoLabelPipeline(
    train_csv_path="datasets/splits/train.csv",
    output_dir="data/pseudo_labels"
)

# Generate with full validation
proposals = pipeline.generate_all_proposals_with_validation()

# Save results
pipeline.save_metadata(proposals)
pipeline.export_yolo_format_validated(proposals)
```

### Step 2: Read Results
```bash
cat phase3/data/pseudo_labels/validation_report.json
```

### Step 3: STOP AND REVIEW
- Check actual proposal counts
- Review failure reasons
- Inspect OCR evidence for low-confidence proposals
- Examine YOLO labels (random sample)
- Decide: proceed with training or refine generation?

**Do NOT train until results reviewed and approved.**

---

## Approval Checklist (REVISED)

- [ ] Evidence recording approach acceptable (OCR text + reasoning)?
- [ ] Dimension validation before variant propagation acceptable?
- [ ] Validation criteria (box size, coordinates, YOLO format) acceptable?
- [ ] Results reporting structure (actual numbers, no estimates) acceptable?
- [ ] Confidence basis explanation approach acceptable?
- [ ] Forged field flagging (confidence 0.15) acceptable?
- [ ] Stop after generation (before training) acceptable?
- [ ] Ready to implement 4 new files + 1 .gitignore update?

**Key Change**: All estimates removed. Only actual measurement-based results will be reported.

