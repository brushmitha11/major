# PHASE 3 REGISTRATION V1 — FINAL DESIGN CORRECTIONS

**Status:** Design ready for implementation approval

---

## CORRECTION 1: STAGE 1 PLAUSIBILITY ASSESSMENT (NO HARD GATE)

### Revised Logic (Evidence-Based, Not Threshold-Based):

```
Input: Geometry-validated quadrilateral (min_sep >= 10, area >= 100)

[1A] Collect Plausibility Evidence
    ├─ Metric 1: Area Coverage
    │   area_coverage_pct = 100 * candidate_area / image_area
    │   Report: e.g., "0.14% of image" or "15% of image"
    │
    ├─ Metric 2: Boundary Proximity
    │   For each corner (TL, TR, BR, BL):
    │     distance_to_boundary = min distance to any image edge
    │   has_boundary_proximity = any corner is close to an edge
    │   Report: e.g., "TL=10px from edge, TR=2000px from edge" → has proximity
    │
    └─ Metric 3: Aspect Ratio Consistency
        image_ar = w / h
        candidate_ar = candidate_width / candidate_height
        ar_ratio = candidate_ar / image_ar
        ar_diff = |log(ar_ratio)|
        consistency_evidence = ar_diff (lower is better)
        Report: e.g., "AR differs 0.3 (within 2x factor)"

[1B] Qualitative Plausibility Assessment (NO HARD THRESHOLDS)
    
    Combine evidence to make assessment:
    
    ┌─────────────────────────────────────────────────────────────────┐
    │ LIKELY BOUNDARY if:                                             │
    │  • area coverage > 2-3% (document should be substantial)        │
    │  • AND at least 2 corners have boundary proximity               │
    │  • AND aspect ratio consistent (log diff < 1.0)                 │
    │                                                                  │
    │ → Accept Stage 1 result                                         │
    │                                                                  │
    │ UNCERTAIN if:                                                   │
    │  • exactly 2 out of 3 evidence metrics are strong               │
    │  • e.g., good coverage + good proximity, but AR mismatch       │
    │  • e.g., good coverage + good AR, but no boundary proximity    │
    │                                                                  │
    │ → Continue to Stage 2 (seek confirmation from Hough)           │
    │                                                                  │
    │ LIKELY ARTIFACT if:                                             │
    │  • area coverage < 1% (internal artifact)                       │
    │  • OR no boundary proximity (internal or corner-focused)        │
    │  • OR significant aspect ratio deviation (log diff > 1.5)       │
    │  • e.g., the AXIS 57×62 (0.14% coverage, no boundary prox)    │
    │                                                                  │
    │ → Continue to Stage 2 (don't trust Stage 1 alone)              │
    └─────────────────────────────────────────────────────────────────┘

[1C] Decision
    IF "LIKELY BOUNDARY":
        └─ Return ordered corners [TL, TR, BR, BL]
           ✓ Stage 1 detection complete
    
    ELSE (UNCERTAIN or LIKELY ARTIFACT):
        └─ Return None → Continue to Stage 2
           (Seek confirmation from independent method)

[1D] Diagnostic Output
    Report all metrics and qualitative assessment:
    ┌──────────────────────────────────────────────────────────────┐
    │ Stage 1 Plausibility Assessment:                             │
    │                                                               │
    │ Geometry validation: PASS                                    │
    │                                                               │
    │ Evidence collected:                                          │
    │   • Area coverage: 0.14% of image                            │
    │   • Boundary proximity: TL=1800px, TR=450px, BR=450px,       │
    │                         BL=1800px (no corner < 400px)        │
    │   • Aspect ratio: candidate=0.92, image=2.19, diff=0.84     │
    │                                                               │
    │ Qualitative assessment: LIKELY ARTIFACT                      │
    │   Reason: Area coverage 0.14% << typical document            │
    │           No corners close to image boundary                 │
    │                                                               │
    │ → Continue to Stage 2                                        │
    └──────────────────────────────────────────────────────────────┘
```

### Key Design Points:

- **No hard 5% gate** — Evidence is reported, not hard-coded
- **Qualitative judgment** — "LIKELY BOUNDARY", "UNCERTAIN", "LIKELY ARTIFACT"
- **Ranges, not thresholds** — "2-3% coverage", "log diff < 1.0" are guidance, not operational gates
- **Evidence-based reasoning** — Diagnostics show WHY a candidate is accepted or rejected
- **Continues to Stage 2** — When uncertain or implausible, rather than failing immediately

---

## CORRECTION 2: STAGE 3 ACCEPTANCE LOGIC (WITH PLAUSIBILITY CHECK)

### Revised Algorithm:

```
Input: Grayscale cheque image

[3A] Morphological Closing
    ├─ Kernel: 5×5
    ├─ Operation: cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    └─ Output: closed_edges

[3B] Contour Detection
    ├─ Find contours in closed_edges
    ├─ Approximate each to quadrilateral
    ├─ Filter: convex + geometry validation (min_sep >= 10, area >= 100)
    └─ Select: largest by area

[3C] If no valid quadrilateral found
    └─ Return None (registration failure)

[3D] NEW: Plausibility Assessment on Stage 3 Candidate
    │
    ├─ Apply SAME plausibility evidence collection as Stage 1:
    │   • Area coverage
    │   • Boundary proximity
    │   • Aspect ratio consistency
    │
    ├─ Qualitative assessment: LIKELY BOUNDARY / UNCERTAIN / LIKELY ARTIFACT
    │
    └─ Decision:
        │
        IF "LIKELY BOUNDARY" or "UNCERTAIN":
        │   └─ Return ordered corners [TL, TR, BR, BL]
        │      ✓ Stage 3 detection complete
        │
        ELIF "LIKELY ARTIFACT":
        │   └─ Return None (registration failure)
        │      Diagnostic: "Morphology recovered a quad, but it is
        │                  an internal artifact, not document boundary."
        │
        └─ End of pipeline

[3E] Diagnostic Output
    Report candidate assessment:
    ┌──────────────────────────────────────────────────────────────┐
    │ Stage 3 Morphological + Contour Retry:                       │
    │                                                               │
    │ Candidate quadrilateral found: YES                           │
    │ Geometry validation: PASS                                    │
    │                                                               │
    │ Plausibility Assessment:                                     │
    │   • Area coverage: 8.5% of image                             │
    │   • Boundary proximity: TL=50px, TR=80px, BR=70px, BL=60px   │
    │   • Aspect ratio: candidate=2.0, image=2.19, diff=0.09      │
    │                                                               │
    │ Qualitative assessment: LIKELY BOUNDARY                      │
    │   Reason: Morphological closing connected broken edges       │
    │           Resulting quad is large and has boundary proximity │
    │           Aspect ratio matches image well                    │
    │                                                               │
    │ → Accept Stage 3 result                                      │
    └──────────────────────────────────────────────────────────────┘
```

### Key Design Points:

- **Same plausibility logic** — Stages 1 and 3 use identical evidence collection
- **No blind acceptance** — Morphology can recover boundaries, but candidate is still assessed
- **Tolerates uncertainty** — If Stage 3 returns "UNCERTAIN", that's acceptable (final attempt)
- **Rejects clear artifacts** — If morphology produces a large internal artifact, reject it
- **Explicit failure** — If all stages fail (including Stage 3), return None → registration failure

---

## PIPELINE OVERVIEW (WITH CORRECTIONS APPLIED)

```
detect_cheque_corners_v1(image)
    ↓
[STAGE 1] Contour-based + Plausibility Assessment
    ├─ Find largest geometry-valid quadrilateral
    ├─ Collect evidence: area coverage, boundary proximity, aspect ratio
    ├─ Assess: LIKELY BOUNDARY / UNCERTAIN / LIKELY ARTIFACT
    │
    ├─ If LIKELY BOUNDARY:
    │   └─ ✓ Return corners
    │
    └─ Else (UNCERTAIN or ARTIFACT):
        └─ Continue to Stage 2
            ↓
[STAGE 2] Hough Line Detection
    ├─ Detect 4 edges (allow ±15° skew)
    ├─ Compute corner intersections
    ├─ Apply geometry validation
    ├─ Success: return corners
    │
    └─ Failure: Continue to Stage 3
        ↓
[STAGE 3] Morphological + Contour Retry + Plausibility
    ├─ Morphological closing
    ├─ Find largest geometry-valid quadrilateral
    ├─ Collect evidence: area coverage, boundary proximity, aspect ratio
    ├─ Assess: LIKELY BOUNDARY / UNCERTAIN / LIKELY ARTIFACT
    │
    ├─ If LIKELY BOUNDARY or UNCERTAIN:
    │   └─ ✓ Return corners (final attempt)
    │
    └─ If LIKELY ARTIFACT:
        └─ Return None → Registration failure
            ↓
[RESULT]
    ├─ Corners found: Proceed to affine transform
    └─ None (all stages failed): Mark as registration failure, route to manual review
```

---

## PROVISIONAL DIAGNOSTIC RANGES (NOT OPERATIONAL THRESHOLDS)

**For reference during development only — NOT validated:**

| Evidence | Indicator | Rationale |
|----------|-----------|-----------|
| Area coverage | > 2-3% suggests boundary | Document should be substantial vs. internal artifacts (57×62 = 0.14%) |
| Boundary proximity | ≥ 2 corners < 400px | Document corners tend toward perimeter |
| Aspect ratio | log(diff) < 1.0 | 2x tolerance is generous for cheque shapes |

**These are developmental guidance, NOT operational thresholds. Not to be used as hard gates in production without validation.**

---

## EXACT FILES TO MODIFY/CREATE

### Modify:
- `phase3/localization/registration.py`
  - Refactor existing `detect_cheque_corners()` → `_detect_corners_stage1_contour()`
  - Add `_assess_boundary_plausibility()` → returns (assessment_category, evidence_dict, reason_string)
  - Add `_detect_corners_stage2_hough()`
  - Add supporting functions: `_classify_line_orientation()`, `_line_intersection()`
  - Add `_detect_corners_stage3_morphological()`
  - Add wrapper `detect_cheque_corners_v1()` (or rename to `detect_cheque_corners`)
  - Preserve all other functions unchanged

### Create:
- `phase3/diagnostic_boundary_detection_v1.py`
  - TRAIN-only diagnostic script
  - Tests 4 representative TRAIN images (Axis, Canara, ICICI, Syndicate)
  - Reports per-stage results with plausibility assessments
  - No validation/test data access

---

## EXACT DIAGNOSTIC COMMAND

```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque
python phase3/diagnostic_boundary_detection_v1.py
```

**Output:** TRAIN-only analysis with per-stage plausibility assessments and decisions.

---

## WHAT EACH FUNCTION RETURNS

### `_assess_boundary_plausibility(quad_pts, image_shape, candidate_area) → (assessment, evidence_dict, reason)`

Returns:
```python
(
    assessment="LIKELY_BOUNDARY" | "UNCERTAIN" | "LIKELY_ARTIFACT",
    evidence={
        'area_coverage_pct': float,
        'has_boundary_proximity': bool,
        'corners_near_boundary': list,
        'aspect_ratio_diff': float,
        'aspect_ratio_consistent': bool,
    },
    reason="Human-readable explanation"
)
```

### `detect_cheque_corners_v1(image) → Optional[List[Tuple[int, int]]]`

Returns:
```python
None if all stages fail
OR
[(TL_x, TL_y), (TR_x, TR_y), (BR_x, BR_y), (BL_x, BL_y)] if any stage succeeds
```

---

## PRESERVATION CHECKLIST

✓ No image-bounds fallback
✓ Hough ±15° provisional skew tolerance
✓ All Hough parameters provisional/unvalidated
✓ Existing geometry safeguards preserved (min_sep=10, area>=100)
✓ Deterministic TL/TR/BR/BL corner ordering
✓ Existing affine transformation unchanged
✓ Existing confidence computation unchanged
✓ Existing scoring function unchanged
✓ TRAIN-only development (no validation/test access)
✓ No dataset/image modification
✓ No locked CSV modification
✓ Explicit failure (None) when all stages fail
✓ No hard area-coverage threshold (5% removed)
✓ Plausibility assessment applied to both Stage 1 and Stage 3

---

## READY FOR IMPLEMENTATION

**Approved design changes:**
1. Stage 1: Plausibility assessment (evidence-based, no hard gates)
2. Stage 3: Plausibility assessment (don't blindly accept morphology results)

**Files to modify:**
- `phase3/localization/registration.py`

**Files to create:**
- `phase3/diagnostic_boundary_detection_v1.py`

**Command to test:**
- `python phase3/diagnostic_boundary_detection_v1.py`

**Awaiting final approval to proceed with implementation.**

