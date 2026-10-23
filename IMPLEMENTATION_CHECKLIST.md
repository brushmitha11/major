# Implementation Checklist: Automated Pseudo-Label Pipeline

**Status**: AWAITING APPROVAL  
**Timeline**: 
- Implementation: 1-2 hours (if approved)
- Proposal generation: ~2-3 minutes
- Quality measurement: ~1 hour (manual sampling)
- Total time to training-ready: ~1.5 hours

---

## Files to CREATE (4 New Files)

### 1. `phase3/ocr_proposal_generator.py`
```
Purpose: Generate bounding box proposals using EasyOCR + pattern matching
Size: ~250 lines
Dependencies: easyocr, cv2, numpy, pytesseract (optional fallback)
Key Functions:
  - OCRProposalGenerator.detect_text_regions(image)
  - OCRProposalGenerator.cluster_by_field_pattern(texts, positions)
  - OCRProposalGenerator.generate_proposals(image_path) → {field: {box, confidence, ocr_value}}
```

### 2. `phase3/variant_propagation_manager.py`
```
Purpose: Propagate proposals from parent reference images to forgery variants
Size: ~180 lines
Dependencies: csv, pathlib, json
Key Functions:
  - VariantPropagationManager.load_train_csv()
  - VariantPropagationManager.propagate_parent_to_variant(parent_proposals, forgery_type)
  - VariantPropagationManager.process_all_variants(reference_proposals) 
       → {variant_uid: proposals}
  - VariantPropagationManager.adjust_confidence_for_forged_field(field, forgery_type)
       → reduced confidence for forged regions
```

### 3. `phase3/pseudo_label_pipeline.py`
```
Purpose: Orchestrate end-to-end proposal generation for all 315 images
Size: ~350 lines
Dependencies: ocr_proposal_generator, variant_propagation_manager, cv2, json
Key Functions:
  - PseudoLabelPipeline.generate_all_proposals()
      1. Load train.csv
      2. Generate template proposals (using existing ChequeFieldExtractorV2)
      3. Generate OCR proposals (new)
      4. Fuse both (average confidence, take best box)
      5. Propagate to variants
      6. Save to metadata.json
  - PseudoLabelPipeline.export_yolo_format()
      → Create yolo/train/*.txt files (YOLO format)
  - PseudoLabelPipeline.save_metadata()
      → Save all proposals to phase3/data/pseudo_labels/metadata.json
  - PseudoLabelPipeline.quality_estimate(sample_indices) [called later]
      → Calculate precision/recall on sample
```

### 4. `phase3/pseudo_label_sampling_backend.py`
```
Purpose: Web UI backend for manually annotating quality measurement sample
Size: ~180 lines
Dependencies: flask, json, pathlib, annotation_manager
Key Routes:
  - GET /sample/list → return 15-20 selected sample image UIDs
  - GET /sample/<uid> → return image + proposed boxes (side-by-side view)
  - POST /sample/<uid>/annotate → save manual annotations for sample image
  - GET /sample/progress → return progress (X of 15 images annotated)
  - GET /sample/quality-metrics → calculate precision/recall after sampling complete
```

---

## Files to MODIFY (2 Files)

### 1. `phase3/annotation_ui_backend.py`
```
Changes:
  - Add import: from pseudo_label_pipeline import PseudoLabelPipeline
  - Add route: GET /api/pseudo_labels/<uid>
      → Returns pseudo-label proposals for image (from metadata.json)
      → Format: {uid, suggestions: [{field, box, confidence, source}]}
  - Add route: GET /api/compare/<uid>
      → Returns both pseudo and manual side-by-side for comparison
      → Format: {pseudo: {...}, manual: {...}}

Impact: Low - only adds new routes, doesn't modify existing logic
Test: Call new endpoints and verify format
```

### 2. `phase3/annotation_ui.html`
```
Changes:
  - Add checkbox: "Load Pseudo-Labels" (in sidebar, above field list)
  - Add toggle functionality:
      - When OFF: load manually annotated boxes (existing behavior)
      - When ON: load proposed boxes from /api/pseudo_labels/<uid>
  - Visual distinction:
      - Manual verified boxes: Red outline (existing)
      - Pseudo-label boxes: Orange/Yellow outline + "UNVERIFIED" label
  - Allow user to:
      - Accept proposed box → convert to manual annotation + save
      - Reject proposed box → delete and draw manually
      - Edit proposed box → drag to adjust

Impact: Medium - adds UI logic, doesn't break existing flow
Test: Toggle on/off, verify boxes load/render correctly
```

---

## Files to CREATE (Output Directories & Files)

### Output Directory Structure
```
phase3/data/pseudo_labels/
├── metadata.json                    # All proposals (315 images)
├── quality_metrics.json            # Sample measurement results
├── variant_propagation.json        # Parent→variant mapping
└── yolo/
    └── train/
        ├── 309137_reference.txt
        ├── 309137_amount_forgery.txt
        ├── 309137_payee_forgery.txt
        └── ... (315 files total)
```

### .gitignore Update
```
# Add to phase3/.gitignore
data/pseudo_labels/metadata.json
data/pseudo_labels/quality_metrics.json
data/pseudo_labels/variant_propagation.json
data/pseudo_labels/yolo/
```

---

## Execution Workflow

### Step 1: Generate Proposals (Automated)
```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque\phase3
python << 'EOF'
from pseudo_label_pipeline import PseudoLabelPipeline

pipeline = PseudoLabelPipeline(
    train_csv_path="../datasets/splits/train.csv",
    output_dir="data/pseudo_labels"
)

print("[1/3] Generating template proposals...")
template_props = pipeline.generate_template_proposals()  # Uses ChequeFieldExtractorV2

print("[2/3] Generating OCR proposals...")
ocr_props = pipeline.generate_ocr_proposals()  # Uses EasyOCR

print("[3/3] Fusing and propagating...")
all_proposals = pipeline.fuse_proposals(template_props, ocr_props)
all_proposals = pipeline.propagate_to_variants(all_proposals)

print(f"Generated proposals for {len(all_proposals)} images")
pipeline.save_metadata(all_proposals)
pipeline.export_yolo_format(all_proposals)
print("Saved to: phase3/data/pseudo_labels/")
EOF
```

### Step 2: Sample Quality (Semi-Automated)
```bash
# Start sampling UI
cd phase3
python pseudo_label_sampling_backend.py
# Open http://localhost:5001/sample/

# UI automatically:
# 1. Selects 15-20 stratified sample images
# 2. Shows proposed vs. manual side-by-side
# 3. User manually annotates each sample
# 4. Calculates precision/recall automatically
# 5. Saves to phase3/data/pseudo_labels/quality_metrics.json

# Result example:
# {
#   "sample_size": 18,
#   "per_field_precision": {
#     "cheque_number": 0.94,
#     "amount": 0.78,
#     "payee_name": 0.72,
#     ...
#   },
#   "overall_precision": 0.78,
#   "recommendation": "PASS - Precision 78% (threshold 75%)"
# }
```

### Step 3: Review & Proceed to Training
```bash
# Check results
cat phase3/data/pseudo_labels/quality_metrics.json

# If passing (≥75% precision):
# - Proposals ready for YOLO training
# - Use yolo/train/ directory for training

# Next: Install YOLO and train
# pip install ultralytics
# python -m yolo detect train \
#   data=cheque_dataset.yaml \
#   model=yolov8n.pt \
#   epochs=50
```

---

## Key Design Decisions (Already Made)

| Decision | Choice | Reason |
|----------|--------|--------|
| **OCR tool** | EasyOCR | Higher accuracy than Tesseract, already available |
| **Proposal fusion** | Template + OCR | 75% recall vs 45% for OCR alone |
| **Variant handling** | Propagate + adjust | 3x faster, tracks forgery regions |
| **Quality measurement** | Sample 15-20 images | ~1 hour vs 10+ for full annotation |
| **Confidence threshold** | ≥75% precision | Practical sweet spot |
| **Pseudo-label storage** | Separate from manual | Prevents contamination |
| **Forgery field handling** | Mark with confidence 0.25 | Explicit warning, can filter in training |

---

## Risk Assessment

### Risk 1: Low Proposal Quality
**Probability**: Medium  
**Impact**: Cannot train detector reliably  
**Mitigation**: Quality measurement sample (15-20 images) detects this early  
**Contingency**: Stop after step 2, adjust methods, regenerate  

### Risk 2: Forgery Field Contamination
**Probability**: Low  
**Impact**: Model learns incorrect forgery patterns  
**Mitigation**: Flag forged fields with low confidence (0.25)  
**Contingency**: Filter these out during training (confidence > 0.75)  

### Risk 3: Template Region Mismatch
**Probability**: Low  
**Impact**: Boxes don't align with actual cheques  
**Mitigation**: OCR method provides alternative boxes  
**Contingency**: Use OCR boxes only, skip template  

### Risk 4: OCR Failures on Low-Contrast Images
**Probability**: Medium  
**Impact**: Missing proposals for some images  
**Mitigation**: Fall back to template proposals  
**Contingency**: Accept lower coverage on subset of images  

---

## Success Criteria

**Proposal Generation** ✓
- All 315 images have proposals
- Each proposal includes confidence scores
- Saved to phase3/data/pseudo_labels/metadata.json

**Quality Measurement** ✓
- 15-20 images manually annotated
- Precision calculated per field
- Overall precision ≥60% (baseline acceptable)

**Training Readiness** ✓
- YOLO format files created (yolo/train/*.txt)
- Confidence thresholds documented
- Ready to train with `yolo detect train`

---

## Approval Checklist

- [ ] Review AUTOMATED_ANNOTATION_PLAN.md for detailed design
- [ ] Confirm OCR approach (EasyOCR + pattern matching) acceptable
- [ ] Confirm variant propagation strategy acceptable
- [ ] Confirm quality measurement sample size (15-20) reasonable
- [ ] Confirm precision threshold (75%) appropriate
- [ ] Confirm pseudo-label storage/separation approach safe
- [ ] Ready to implement (4 new files + 2 modifications)

**Questions before proceeding:**
1. Any concern about OCR-based proposal accuracy?
2. Should sampling be stratified differently?
3. Any preference for confidence threshold during YOLO training?
4. Timeline acceptable?

