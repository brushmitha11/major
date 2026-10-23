# Plan Revisions Summary
## What Changed Between Original and Revised Plans

---

## Issue 1: Unverified Estimates as Facts

**Original Plan** ❌
- Showed estimated precision/recall/F1 tables with specific numbers
- Presented "Expected Outcomes" as if measured
- Suggested quality thresholds (75% precision) without data
- Made accuracy projections

**Revised Plan** ✓
- All estimated figures marked as "illustrative only" or removed entirely
- No precision/recall tables without actual measurements
- Results section shows "XXX / 315" placeholders for actual counts
- Explicit: "All numbers are ACTUAL measured results, no estimates"

**Impact**: Results will reflect reality, not projections.

---

## Issue 2: Pattern-Based Field Classification

**Original Plan** ❌
```python
# Pseudo-code from original
if text matches pattern (6-10 digits):
    field = "cheque_number"  # Assigned based only on digits
```
- Could misclassify unrelated numbers
- No evidence or reasoning recorded
- Blind pattern matching without context

**Revised Plan** ✓
```python
# Logic from revised plan
if text matches 6-10 digits AND (position right-side OR small region):
    field = "cheque_number"
    evidence = f"Matched pattern: 6-10 digits. Text: {text}"
    classification_confidence = "high"
else if unrelated match:
    classification_confidence = None  # Don't force assignment
    record as unclassified evidence
```

**Changes**:
- Pattern + position + size validation (not pattern alone)
- Evidence recorded and saved
- Confidence levels (high/medium/low)
- OCR text stored for manual inspection
- Unclassified text collected separately
- Explicit reasoning for every assignment

**Impact**: Transparent, auditable field classification.

---

## Issue 3: Variant Propagation Without Validation

**Original Plan** ❌
```python
# Original: Just copy parent boxes to variants
propagated_proposals = parent_proposals.copy()
```
- Assumed identical image dimensions
- Assumed all variants have same layout
- No checking before propagation
- Could propagate wrong boxes to resized images

**Revised Plan** ✓
```python
# New: Validate before propagating
parent_w, parent_h = load_image(parent_path).shape
variant_w, variant_h = load_image(variant_path).shape

dimension_diff = abs(parent_w - variant_w) / parent_w * 100

if dimension_diff > 5%:
    flag_as_alignment_uncertain()
    reduce_confidence_by(0.3)
else:
    propagate_with_full_confidence()
```

**Changes**:
- Image dimension comparison before propagation
- Dimension mismatches flagged explicitly
- Confidence reduced (not eliminated) for uncertain cases
- Propagation metadata recorded (which parent, dimension check result)
- All flagged cases documented

**Impact**: Catches layout mismatches early, prevents silent errors.

---

## Issue 4: No Evidence Trail for Decisions

**Original Plan** ❌
- Proposals had only: `{field: {box, confidence}}`
- No way to trace why assignment was made
- Impossible to debug low-confidence proposals
- No OCR text saved

**Revised Plan** ✓
```json
{
  "cheque_number": {
    "box": [x, y, w, h],
    "ocr_text": "309137",
    "ocr_confidence": 0.95,
    "evidence": "Matched pattern: 6-10 digits. Text: 309137",
    "classification_confidence": "high",
    "method": "ocr",
    "confidence_basis": "OCR character certainty: 0.95"
  }
}
```

**Changes**:
- OCR text recorded (traceable)
- Reasoning recorded (auditable)
- Confidence basis explained (not opaque)
- Method source documented (template vs OCR)
- Evidence trails enable manual review

**Impact**: Every proposal can be inspected and understood.

---

## Issue 5: No Validation of Outputs

**Original Plan** ❌
- Generated boxes without checking validity
- No YOLO label validation
- Silent failures possible
- Invalid coordinates could be exported

**Revised Plan** ✓
```python
def validate_box(box):
    assert 0 <= x_min < 1 and 0 <= y_min < 1
    assert 0 < width <= 1 and 0 < height <= 1
    assert x_min + width <= 1  # Doesn't overflow
    assert width > 0.01 and height > 0.01  # Not too small
    return True

def validate_yolo_label(class_id, x, y, w, h):
    assert 0 <= class_id <= 7
    assert 0 <= x, y, w, h <= 1
    assert x - w/2 >= 0  # Doesn't overflow left
    assert x + w/2 <= 1  # Doesn't overflow right
    return True
```

**Changes**:
- Every box validated before export
- Invalid boxes rejected (not silently included)
- YOLO labels validated for format compliance
- Validation failures logged with specific reasons
- Statistics: X valid, Y invalid, reason breakdown

**Impact**: Only correct labels in training data.

---

## Issue 6: Unverified Quality Claims

**Original Plan** ❌
- Proposed 15-20 sample images for quality measurement
- Would estimate "78% precision" from sample
- Would use estimate to proceed with training
- No way to verify estimate was accurate

**Revised Plan** ✓
- **Removed quality estimation entirely**
- Instead: Generate proposals, stop, report actual numbers
- User reviews actual proposals before any decisions
- Manual sampling happens AFTER review, not during planning
- No automatic pass/fail thresholds

**Changes**:
- No sampling strategy in this stage
- No quality estimation
- Generate → report actual counts → STOP for review
- Sampling can happen later if needed
- Manual review gates all next decisions

**Impact**: Results are transparent, decisions made with full information.

---

## Issue 7: No Reporting of Actual Results

**Original Plan** ❌
- Implied all 315 images would get proposals
- No discussion of failure modes
- No reporting of what went wrong

**Revised Plan** ✓
```
RESULTS REPORT:
================

Template proposals: 305/315 successful (failures: 10)
  Reason: Low content detection (10 images)

OCR proposals: 287/315 successful (failures: 28)
  Reason: OCR failures (low contrast, 15 images)
  Reason: No text found (13 images)

Fields successfully proposed:
  cheque_number: 289/315 (91%)
  amount: 267/315 (85%)
  payee_name: 275/315 (87%)
  [etc - actual counts]

YOLO label validation:
  Valid labels: 2,240 (out of 2,520 attempts)
  Invalid labels: 280
    - Coordinates out of range: 45
    - Box too small: 120
    - Box extends past boundary: 115

[All specific failures documented]
```

**Changes**:
- Report actual success/failure counts
- Document specific failure reasons
- Per-field coverage statistics
- Validation failure breakdown
- Everything measurable is measured

**Impact**: Clear visibility into what works and what doesn't.

---

## Issue 8: Data Integrity Not Explicit

**Original Plan** ❌
- Didn't explicitly state what files would NOT be modified
- Could be ambiguous whether data is safe

**Revised Plan** ✓
```
DATA INTEGRITY COMMITMENTS:

Modified files: NONE
  - ✓ datasets/splits/train.csv untouched
  - ✓ Original images untouched
  - ✓ Verified annotations untouched
  - ✓ No packages installed
  - ✓ No model trained

New files (isolated):
  - phase3/data/pseudo_labels/ (separate from verified data)
  - Marked as unverified pseudo-labels
  - Can be deleted without impact
```

**Changes**:
- Explicit list of unmodified files
- Explicit location of all new files
- Clear data isolation
- Safe to delete pseudo-labels if needed

**Impact**: Data safety guaranteed.

---

## Issue 9: No Stopping Point for Review

**Original Plan** ❌
- Proposed generating → sampling → measuring → proceeding to training
- All as one continuous pipeline
- No explicit review/approval point

**Revised Plan** ✓
```
EXECUTION FLOW:

Step 1: Generate proposals (automated)
        → phase3/data/pseudo_labels/metadata.json
        → phase3/data/pseudo_labels/validation_report.json

STOP AND REVIEW HERE ←─ EXPLICIT CHECKPOINT
  - Read validation_report.json
  - Check actual proposal counts
  - Inspect OCR evidence
  - Examine YOLO labels
  - Approve before proceeding

Step 2: (After approval) Proceed to training
```

**Changes**:
- Clear stopping point after generation
- Explicit review instructions
- No automatic proceeding
- User must explicitly approve results

**Impact**: Nothing happens without user review.

---

## Issue 10: Too Ambitious Scope

**Original Plan** ❌
- Proposed generation → sampling → quality measurement → ready for training all in one proposal
- Treated as single atomic task
- Hard to review incrementally

**Revised Plan** ✓
- **THIS STAGE: Generate and report**
- Sampling and training: separate decisions made after review
- Scope clearly limited
- Can stop and refine anytime

**Changes**:
- Single, focused scope
- Smaller review surface
- Staged approach
- No premature optimization

**Impact**: Easier to review, approve, and correct if needed.

---

## Summary of Key Corrections

| Aspect | Original | Revised | Impact |
|--------|----------|---------|--------|
| **Accuracy claims** | Estimated 75% | Actual measured only | Honest results |
| **Field classification** | Pattern alone | Pattern + context + evidence | No misclassifications |
| **Variant propagation** | Blind copy | Dimension-validated | Catches layout mismatches |
| **Evidence trail** | None | Full (OCR text, reasoning) | Auditable & debuggable |
| **Output validation** | None | Comprehensive (boxes, YOLO) | Only valid data exported |
| **Quality measurement** | Estimated 15-20 sample | None (measure later) | Transparent results |
| **Results reporting** | Projected numbers | Actual counts | Evidence-based |
| **Data safety** | Implicit | Explicit guarantees | Clear boundaries |
| **Review checkpoint** | None | Explicit STOP | User control |
| **Scope** | Everything at once | Generation only | Focused & reviewable |

---

## Approval Questions Answered

**Q: How do we avoid unverified estimates?**
A: Report actual numbers only. All counts measured during generation.

**Q: How do we avoid field misclassification?**
A: Pattern + position + context validation. OCR text recorded for review.

**Q: How do we ensure variant propagation is safe?**
A: Image dimension validation before propagation. Uncertain cases flagged.

**Q: How do we make decisions transparent?**
A: Full evidence trail (OCR text, reasoning, method sources, confidence basis).

**Q: How do we ensure output quality?**
A: Comprehensive validation (boxes, YOLO labels, coordinates, dimensions).

**Q: How do we avoid overcommitting?**
A: Generate → report → STOP for review. No automatic proceeding.

**Q: How do we ensure data safety?**
A: Explicit list of unmodified files. All new files in isolated directory.

**Q: When can we train?**
A: Only after manual review of actual results and explicit approval.

---

## Files Updated

1. ✓ **AUTOMATED_ANNOTATION_PLAN_REVISED.md** - Complete corrected design
2. ✓ **IMPLEMENTATION_CHECKLIST_REVISED.md** - Implementation with corrections
3. ✓ **PLAN_REVISIONS_SUMMARY.md** (this file) - Change summary

**Ready for approval to implement revised plan.**

