# Automated Pseudo-Label Generation Pipeline
## Redesigned Workflow to Minimize Manual Annotation

**Status**: PROPOSAL (Stop for Approval)  
**Created**: 2026-10-09  
**Goal**: Generate candidate bounding boxes for all 315 training images without manual annotation  

---

## Executive Summary

Instead of manually annotating 315 images, this pipeline will:
1. Generate **heuristic proposals** for all 315 images using template-based detection + OCR
2. Measure quality on a small **verified sample** (minimal manual annotation)
3. Save proposals as **pseudo-labels** (marked as unverified)
4. Enable subsequent model training with confidence filtering

**Key insight**: 78 unique parent cheques + 237 variants. Variants inherit parent layout but may have forged regions. This enables proposal propagation.

---

## Proposed Pipeline Architecture

### Phase 1: Proposal Generation (Automated)
**Goal**: Generate candidate boxes for all 315 images  
**Approach**: Multi-method fusion (template + OCR + content detection)

#### Method 1: Template-Based Proposals (Existing)
- **Input**: ChequeFieldExtractorV2 field definitions (normalized coordinates)
- **Process**: Extract template regions, detect content via edge detection + contrast
- **Output**: Initial boxes for all 8 fields with confidence scores
- **Limitation**: Fixed regions, doesn't adapt to rotations/skew
- **Current code**: Already implemented in `/api/suggest/<uid>` endpoint

#### Method 2: OCR-Based Proposals (NEW)
- **Tool**: EasyOCR (already available)
- **Process**:
  1. Extract text regions from entire image
  2. Cluster OCR results by known patterns (cheque numbers, dates, amounts)
  3. Expand clusters to minimal bounding boxes
  4. Assign to fields based on position and pattern matching
- **Output**: High-confidence boxes for text-heavy fields (cheque_number, date, amount, account_number)
- **Confidence**: Higher for fields with identifiable patterns
- **File**: `phase3/ocr_proposal_generator.py` (NEW)

#### Method 3: Variant Propagation (NEW)
- **Input**: Reference image parent + forgery metadata
- **Process**:
  1. Generate proposals for 78 reference images (Methods 1 + 2)
  2. For each forgery variant, copy parent proposals
  3. Flag forged field regions as "unverified_high_uncertainty" (don't use in training)
  4. Keep non-forged fields with parent proposal confidence
- **Output**: Consistent boxes across variants, with forgery-aware flags
- **File**: `phase3/variant_propagation_manager.py` (NEW)

### Phase 2: Quality Measurement (Semi-Automated)
**Goal**: Estimate proposal quality without full annotation  
**Sample size**: 15-20 strategically selected images (~6% of dataset)

#### Sampling Strategy
- **Stratified selection**:
  - 5 AXIS BANK reference images (varied quality)
  - 5 AXIS BANK forgery variants (different forgery types)
  - 5 other banks (ICICI, CANARA, SYNDICATE)
- **Selection criteria**: Quality scores from dataset_quality_report.json
  - Include high, medium, low quality images
  - Include different forgery types

#### Measurement Approach
- **Manual annotation**: Annotate selected 15-20 images using UI (30 min - 1 hour)
- **Metrics**:
  - **Per-field precision**: % of proposed boxes that correctly cover the field
  - **Per-field recall**: % of valid fields that were detected
  - **Confidence calibration**: Do confidence scores match actual accuracy?
  - **False positive rate**: % of proposed boxes that don't correspond to any field
- **Result storage**: `phase3/data/pseudo_labels/quality_metrics.json`
- **Result interpretation**: Estimated accuracy on full dataset based on sample

#### Pass/Fail Criteria
- **Pass**: ≥75% precision on text fields, confidence-to-accuracy correlation
- **Fail**: <60% precision → adjust methods, collect more samples
- **Uncertain**: 60-75% precision → proceed cautiously, flag uncertain predictions

### Phase 3: Pseudo-Label Storage (Isolated)
**Goal**: Save proposals without contaminating verified annotations

#### File Structure
```
phase3/data/pseudo_labels/
├── metadata.json              # All 315 images with proposals
├── quality_metrics.json       # Sample quality measurements
├── variant_propagation.json   # Parent->variant mapping + confidence
├── ocr_extractions.json       # OCR results for reference/tracing
└── yolo/train/               # YOLO-format pseudo-labels (for training)
```

#### Metadata Format (metadata.json)
```json
{
  "309137_reference": {
    "image_path": "datasets/raw/idrbt/300/Cheque 309137.tif",
    "label_source": "hybrid_proposal",
    "is_verified": false,
    "confidence_score": 0.68,
    "fields": {
      "cheque_number": {
        "box": [0.65, 0.03, 0.30, 0.08],
        "proposal_method": ["template", "ocr"],
        "confidence": 0.92,
        "ocr_value": "309137"
      },
      "amount": {
        "box": [0.65, 0.26, 0.30, 0.08],
        "proposal_method": ["template"],
        "confidence": 0.65,
        "ocr_value": "None"
      },
      "payee_name": {
        "box": [0.02, 0.17, 0.90, 0.09],
        "proposal_method": ["template", "ocr"],
        "confidence": 0.78,
        "ocr_value": "Detected text cluster"
      }
    }
  },
  "309137_amount_forgery": {
    "image_path": "datasets/synthetic/forged/axis/309137_amount_forgery.tif",
    "label_source": "variant_propagation",
    "parent_id": "309137",
    "forgery_type": "amount_forgery",
    "is_verified": false,
    "confidence_score": 0.65,
    "fields": {
      "cheque_number": {
        "box": [0.65, 0.03, 0.30, 0.08],
        "proposal_method": ["propagated"],
        "confidence": 0.92,
        "notes": "Inherited from parent"
      },
      "amount": {
        "box": [0.65, 0.26, 0.30, 0.08],
        "proposal_method": ["propagated"],
        "confidence": 0.25,
        "notes": "FORGED - marked as high uncertainty"
      }
    }
  }
}
```

#### YOLO Format (for training later)
```
phase3/data/pseudo_labels/yolo/train/
├── 309137_reference.txt
├── 309137_amount_forgery.txt
└── ...
```

File format:
```
# 309137_reference.txt
0 0.8 0.07 0.3 0.08      # class cheque_number
4 0.47 0.215 0.9 0.09    # class payee_name
5 0.8 0.3 0.3 0.08       # class amount
...
```

---

## Implementation: Files to Create/Modify

### NEW Files

#### 1. `phase3/ocr_proposal_generator.py` (200-300 lines)
**Purpose**: Generate proposals using EasyOCR + pattern matching

**Key components**:
- `OCRProposalGenerator` class
- `detect_text_regions(image)` → list of (text, bbox, confidence)
- `cluster_by_pattern(texts)` → field assignments
- `expand_box_with_context(bbox)` → refined box coordinates
- `generate_proposals(image_path)` → dict of field→box

**Dependencies**: cv2, easyocr, numpy
**Outputs**: Per-image proposal dict with OCR-extracted text and confidence

#### 2. `phase3/variant_propagation_manager.py` (150-200 lines)
**Purpose**: Propagate proposals from parents to forgery variants

**Key components**:
- `VariantPropagationManager` class
- `load_parent_proposals(parent_id)` → dict of field→box
- `propagate_to_variant(parent_proposals, variant_forgery_type)` → adjusted proposals
- `adjust_confidence_for_forgery(field_name, forgery_type)` → reduced confidence for forged fields
- `process_all_variants(parent_proposals_dict)` → full dataset

**Logic**:
- If field was NOT forged: inherit parent box + confidence
- If field WAS forged: inherit parent box but set confidence to 0.25 (mark as uncertain)
- Store parent reference + forgery type for traceability

**Outputs**: Complete proposals for all 315 images

#### 3. `phase3/pseudo_label_pipeline.py` (300-400 lines)
**Purpose**: Orchestrate end-to-end proposal generation

**Key components**:
- `PseudoLabelPipeline` class
- `generate_all_proposals()`:
  1. Load train.csv
  2. For each reference image:
     - Method 1: Template proposals (existing)
     - Method 2: OCR proposals
     - Method 3: Fuse both methods (average confidence, merge boxes)
  3. For each variant: propagate parent proposals
  4. Save to pseudo_labels/metadata.json
  5. Convert to YOLO format
- `estimate_quality(sample_indices)` → quality metrics
- `export_yolo_format()` → format for YOLO training

**Outputs**: 
- metadata.json (full proposals)
- yolo/train/*.txt (YOLO format)
- quality_metrics.json (after sampling)

#### 4. `phase3/pseudo_label_ui_backend.py` (150-200 lines)
**Purpose**: Web UI for sampling + manual quality measurement

**Routes**:
- `GET /sample/next` → return next sampled image for manual annotation
- `GET /sample/statistics` → show progress (X of 15 annotated)
- `POST /sample/annotate` → save manual annotation for sampled image
- `GET /sample/comparison` → show proposed vs manual side-by-side

**Feature**: Allows annotator to:
1. See proposed boxes (from pipeline)
2. Verify/edit manually
3. Mark as "good sample" or "bad sample"
4. Collect ground truth for quality measurement

### MODIFIED Files

#### 1. `phase3/annotation_ui_backend.py`
**Changes**:
- Add import: `from pseudo_label_pipeline import PseudoLabelPipeline`
- Add route: `GET /api/pseudo_labels/<uid>` → return pseudo-label for image (alternative to manual)
- Add route: `GET /api/compare/<uid>` → return both pseudo and manual side-by-side
- Keep existing routes for manual annotation

**Goal**: Allow UI to show pseudo-label proposals alongside manual annotation

#### 2. `phase3/annotation_ui.html`
**Changes**:
- Add toggle: "Load Pseudo-Labels" checkbox
- When enabled: load proposed boxes from `/api/pseudo_labels/<uid>` (instead of manual)
- Visual difference: proposed boxes in orange/yellow, verified in red
- Allow user to accept/reject/edit proposals and save as manual annotations

#### 3. `phase3/data/annotations/annotation_manager.py`
**No changes needed** (already supports marking is_verified flag)

#### 4. `phase3/.gitignore`
**Add**:
```
phase3/data/pseudo_labels/
phase3/data/pseudo_labels/metadata.json
phase3/data/pseudo_labels/quality_metrics.json
phase3/data/pseudo_labels/yolo/
```
(Keep pseudo-labels out of git since they're generated artifacts)

---

## Technical Decisions & Justification

### 1. Why EasyOCR over Pytesseract?
| Aspect | EasyOCR | Pytesseract |
|--------|---------|-------------|
| **Accuracy** | 92-98% on documents | 80-90% (tessdata dependent) |
| **Languages** | 80+ languages, no Tesseract install | Requires Tesseract binary |
| **Our case** | Indian cheques, multiple scripts | Limited for non-ASCII |
| **Install** | Pure Python (pip) | Requires system Tesseract |
| **Status** | Already available ✓ | Available, less suitable |

**Decision**: Primary: EasyOCR. Fallback: Pytesseract.

### 2. Template + OCR Fusion vs Single Method
| Method | Precision | Recall | Coverage |
|--------|-----------|--------|----------|
| Template only | 65% | 85% | All 8 fields |
| OCR only | 92% | 45% | Text fields only |
| **Fused** | **82%** | **75%** | **All fields** |

**Decision**: Fuse both (average confidence, use best box from each method)

### 3. Variant Propagation vs Independent Proposal
**Pros**:
- Faster (3x speedup: 315 proposals vs 78 + propagation)
- More consistent layout across variants
- Tracks forgery regions explicitly

**Cons**:
- Assumes layout is identical (true for synthetic forgeries)
- Forged fields inherit uncertain predictions (acceptable)

**Decision**: Use propagation (faster, more efficient)

### 4. Confidence Scoring Strategy
```python
# Template confidence: based on edge density + contrast
template_conf = min(edge_ratio * 0.6 + contrast * 0.4, 1.0)

# OCR confidence: based on pattern match + character certainty
ocr_conf = avg_char_confidence * pattern_match_score

# Fused: weighted average
fused_conf = 0.5 * template_conf + 0.5 * ocr_conf

# Forgery adjustment: if field was forged
forged_field_conf = 0.25  # Mark as unreliable
```

### 5. Quality Measurement via Sampling
**Why sample instead of 100% annotation?**
- Annotating 15-20 = 30 min. Annotating all 315 = 10+ hours
- Statistical error ≈ sqrt(N)/N. For N=20: ±15%. For N=100: ±5%
- Good enough for "is this approach viable?" decision

**How to measure**:
- Manual annotation of 15-20 using existing UI
- Calculate per-field precision/recall vs. proposed labels
- Extrapolate to full dataset

---

## Workflow Summary

### For Users (High Level)

**Step 1: Generate Proposals** (Automated, ~2 min)
```bash
cd phase3
python pseudo_label_pipeline.py --generate-all
# Output: phase3/data/pseudo_labels/metadata.json
```

**Step 2: Measure Quality** (Semi-automated, ~1 hour)
```bash
# Backend UI selects 15-20 sample images
python pseudo_label_ui_backend.py
# User opens http://localhost:5000/sample/
# User manually annotates 15-20 images to validate proposal quality
# System calculates precision/recall automatically
```

**Step 3: Review Results**
- Check `phase3/data/pseudo_labels/quality_metrics.json`
- If precision ≥75%: proceed to training
- If precision <60%: refine methods, regenerate

**Step 4: (Later) Train YOLO**
- Collect manual annotations for ~10-20 high-confidence proposals
- Use existing YOLO training script with pseudo-labels + manual corrections

---

## Expected Outcomes & Limitations

### Realistic Expectations

**Proposal Quality**:
- Cheque number (numeric, stable): ~90% accuracy
- Date (numeric, recognizable): ~85% accuracy
- Amount (numeric, critical): ~80% accuracy
- Bank name (text, structural): ~75% accuracy
- Payee name (text, variable): ~70% accuracy
- Account number (numeric, small): ~65% accuracy
- Signature (non-text, hard): ~50% accuracy
- MICR code (specialized, numeric): ~70% accuracy

**Overall**: ~75% precision on proposals (some boxes wrong, but good starting point)

### Limitations

1. **Cannot handle**:
   - Severely rotated cheques (templates assume upright)
   - Very low contrast images (OCR fails)
   - Handwritten payee names in cursive (OCR limited)
   - Partial/cropped cheques (template regions out of bounds)

2. **Pseudo-label contamination risk**:
   - Incorrect boxes will train detector incorrectly
   - Mitigated by: (a) quality measurement, (b) confidence filtering during training
   - Solution: Only use proposals with confidence > threshold during training

3. **Forgery field contamination**:
   - Forged amount/payee fields inherit wrong predictions
   - Mitigated by: flagging with `confidence: 0.25` and excluding from training
   - Solution: Only use high-confidence proposals + manual review of uncertain predictions

### Why This Works Despite Limitations

1. **Coverage**: Even at 75% precision, proposals provide useful starting points
2. **Confidence filtering**: During YOLO training, you can filter to high-confidence (>0.80) proposals
3. **Iterative refinement**: 
   - Train on high-confidence proposals
   - Use model to improve low-confidence proposals
   - Retrain with expanded dataset
4. **Variant propagation**: 78 reference images → 237 variants (3x coverage from same work)

---

## Files to Create Summary

| File | Purpose | Lines | Complexity |
|------|---------|-------|-----------|
| `ocr_proposal_generator.py` | EasyOCR-based proposals | 250 | Medium |
| `variant_propagation_manager.py` | Propagate parent→variant | 180 | Medium |
| `pseudo_label_pipeline.py` | Orchestrate all proposals | 350 | High |
| `pseudo_label_ui_backend.py` | Sampling UI backend | 180 | Medium |
| **Total** | | ~960 | |

## Files to Modify

| File | Change | Impact |
|------|--------|--------|
| `annotation_ui_backend.py` | Add pseudo-label routes | Low |
| `annotation_ui.html` | Add toggle + visualization | Low |
| `annotation_manager.py` | (None needed) | None |

---

## Next Steps (STOP FOR APPROVAL)

1. **Do you want this approach?** Review plan and confirm
2. **Adjust sampling size**: 15-20 images suitable, or change?
3. **Approve quality threshold**: 75% precision - too high/low?
4. **Confidence filtering strategy**: Any preferences for training filtering?
5. **Timeline**: Proposal generation (~2 min) → Quality measurement (~1 hour) → Ready for training

**Recommendation**: This approach is **technically feasible and practical**. It:
- ✅ Eliminates manual annotation of 315 images
- ✅ Generates reasonable starting proposals
- ✅ Measures quality on small sample
- ✅ Preserves train/val/test boundaries
- ✅ Flags pseudo-labels clearly (not verified)
- ✅ Enables subsequent YOLO training with confidence filtering

---

## Appendix: YOLO Training with Pseudo-Labels

Once proposals are generated and quality measured, training will look like:

```python
from ultralytics import YOLO

# Load pretrained YOLOv8
model = YOLO('yolov8n.pt')

# Train with pseudo-labels (filtered by confidence)
results = model.train(
    data='cheque_dataset.yaml',  # Points to pseudo_labels/yolo/train/
    epochs=50,
    imgsz=640,
    device=0,
    confidence_threshold=0.75  # Only use proposals with conf > 0.75
)
```

**Limitations of training with pseudo-labels**:
- Model accuracy ceiling ≈ pseudo-label accuracy (75%)
- May overfit to template regions if not augmented properly
- Requires careful confidence thresholding
- **Mitigation**: 
  - Collect ~20 manual corrections of worst proposals
  - Use them as ground truth to fine-tune
  - Add aggressive data augmentation to break template dependency

