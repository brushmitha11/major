# PHASE 3 — CLASSICAL BOUNDARY STUDY PLAN

**Status:** Pre-execution plan (awaiting approval)

---

## OBJECTIVE

Determine whether the existing classical V1 boundary detection pipeline can be improved to detect cheque boundaries across all four representative banks WITHOUT:
- Creating annotations
- Training models
- Random parameter tuning
- Overfitting to these 4 images

**Question to answer:** Can small, predefined classical CV strategies recover cheque boundaries on Canara/ICICI/Syndicate?

---

## DATA RESTRICTION

**TRAIN-only. Four fixed images:**

1. `datasets/raw/idrbt/300/Cheque 309137.tif` — AXIS BANK
2. `datasets/raw/idrbt/300/Cheque 120612.tif` — CANARA BANK
3. `datasets/raw/idrbt/300/Cheque 100829.tif` — ICICI BANK
4. `datasets/raw/idrbt/300/Cheque 083657.tif` — SYNDICATE BANK

**Forbidden:**
- ❌ validation.csv (will NOT be accessed)
- ❌ test.csv (will NOT be accessed)
- ❌ validation images (will NOT be accessed)
- ❌ test images (will NOT be accessed)
- ❌ Modifying locked CSV files
- ❌ Modifying original dataset images
- ❌ Creating new annotations

---

## FILES TO BE CREATED

**New diagnostic script only:**
- `phase3/diagnostic_classical_boundary_study.py` (500-800 lines)

This script will:
- Implement 4 experimental strategies
- Run each on 4 images
- Compare results
- Generate comparison table

---

## FILES THAT WILL NOT BE MODIFIED

**Approved baseline preserved:**
- ❌ `phase3/localization/registration.py` (baseline stays intact for comparison)
- ❌ `phase3/localization/templates.py`
- ❌ `phase3/localization/crops.py`
- ❌ `datasets/splits/train.csv`
- ❌ `datasets/splits/validation.csv`
- ❌ `datasets/splits/test.csv`
- ❌ All original dataset images

---

## EXPERIMENT PLAN

### **EXPERIMENT 0: CURRENT BASELINE V1**

**What:** Run existing V1 detector exactly as implemented

**Process:**
1. Import approved `detect_cheque_corners()` from registration.py
2. Run on each of 4 TRAIN images
3. Record results

**Metrics:**
- Success/failure
- Detection stage (1/2/3 or None)
- Detected width × height
- Area coverage %
- Plausibility assessment
- Corner coordinates
- Failure reason

---

### **EXPERIMENT 1: ADAPTIVE EDGE PREPROCESSING + CONTOUR**

**Concept:** Better edge detection preprocessing, same contour logic

**Preprocessing strategies (try each):**
1. Grayscale
2. Gaussian blur (5×5) + grayscale
3. Median filter (5×5) + grayscale
4. Otsu adaptive threshold + morphological closing
5. Bilateral filter (for edge-preserving smoothing)

**Process:**
1. Apply preprocessing
2. Canny edge detection (50, 150 — unchanged)
3. Find contours
4. Approximate to quadrilaterals
5. Apply EXISTING geometry safeguards (min_sep=10, area>=100)
6. Apply EXISTING plausibility assessment
7. Select best candidate (NOT just largest)
8. Return corners or None

**Key constraint:** Do NOT accept candidate solely because it is largest.

**Expected outcome:** Better edge isolation → valid quadrilaterals survive filters

---

### **EXPERIMENT 2: MULTI-SCALE HORIZONTAL/VERTICAL LINE EVIDENCE**

**Concept:** Hough lines at predefined scales to handle different feature sizes

**Scales to test (FIXED, not searched):**
- 0.5 (half resolution)
- 1.0 (original resolution)
- 1.5 (1.5× resolution via upscaling)

**Process at each scale:**
1. Resize image to scale
2. Canny edge detection (50, 150)
3. Hough line detection (existing Hough params)
4. Classify lines as horizontal/vertical (±15°)
5. Find 4 main edges (top/bottom/left/right)
6. Compute corner intersections
7. Apply geometry safeguards
8. Apply plausibility assessment
9. Combine evidence across scales (prefer consistent detection)

**Key constraint:** Only 3 scales, not continuous search

**Expected outcome:** Document boundaries become detectable at different resolutions

---

### **EXPERIMENT 3: MORPHOLOGICAL CLOSING + CONTOUR**

**Concept:** Different morphology kernels to connect broken edges

**Kernels to test (FIXED):**
- 3×3
- 5×5
- 7×7

**Process for each kernel:**
1. Canny edge detection (50, 150)
2. Morphological closing with kernel
3. Find contours
4. Approximate to quadrilaterals
5. Apply existing geometry safeguards
6. Apply existing plausibility assessment
7. Select best candidate (NOT just largest)

**Key constraint:** Only 3 kernels, no optimization

**Expected outcome:** Different closing strengths recover different boundary traces

---

### **EXPERIMENT 4: COMBINED EDGE + LINE EVIDENCE**

**Concept:** Integrate contour and line evidence without hard thresholds

**Process:**
1. Run Experiment 1 preprocessing + contour → candidate C1
2. Run Experiment 2 Hough at scale 1.0 → candidate C2
3. Run Experiment 3 morphology 5×5 → candidate C3
4. Collect evidence for each:
   - Quadrilateral/contour validity
   - Horizontal boundary evidence
   - Vertical boundary evidence
   - Boundary proximity
   - Area coverage
   - Aspect ratio consistency
5. Select candidate with strongest combined evidence
6. Apply plausibility assessment
7. Return if plausible

**Key constraint:** NO new hard thresholds, only existing plausibility logic

**Expected outcome:** Redundant evidence improves robustness

---

## COMPARISON TABLE STRUCTURE

```
| Bank | Baseline V1 | Exp 1 | Exp 2 | Exp 3 | Exp 4 |
|------|-------------|-------|-------|-------|-------|
| AXIS |  SUCCESS | | | | |
| CANARA | FAILURE | | | | |
| ICICI | FAILURE | | | | |
| SYNDICATE | FAILURE | | | | |
| Baseline success rate: 1/4 | | | | |
```

---

## SUCCESS CRITERIA (PER EXPERIMENT)

**NOT:** "algorithm returned four corners"

**IS:** Evidence indicates corners represent the COMPLETE CHEQUE boundary, not internal artifacts

**Evaluation:**
1. Detected region covers substantial portion of image (>10% coverage)
2. Corners near image perimeter (consistent with document boundary)
3. Aspect ratio similar to image (not extreme distortion)
4. Bounding box width/height ratio sensible for cheque (not tall vertical stripe)
5. No obvious internal structure (text box, stamp, ruling)

---

## EXACT FILES TO CREATE

**One new file only:**

```
phase3/diagnostic_classical_boundary_study.py
├─ Imports:
│  ├─ cv2, numpy
│  ├─ existing _order_corners_deterministic()
│  ├─ existing _validate_quadrilateral_geometry()
│  ├─ existing _assess_boundary_plausibility()
│  ├─ detect_cheque_corners() from approved baseline
│
├─ Load 4 TRAIN images from CSV
│
├─ Experiment 0: Run baseline
├─ Experiment 1: Adaptive preprocessing variants
├─ Experiment 2: Multi-scale Hough
├─ Experiment 3: Morphology kernels
├─ Experiment 4: Combined evidence
│
└─ Report comparison table
```

---

## EXACT COMMANDS TO RUN

**Setup (one time):**
```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque
```

**Execute study:**
```bash
python phase3/diagnostic_classical_boundary_study.py
```

**Expected output:**
- Per-image results for each experiment
- Comparison table (Baseline vs Exp 1-4)
- Success rate per experiment
- Failure analysis
- Go/No-Go recommendation

---

## CONFIRMATION: NO VALIDATION/TEST ACCESS

This script will:
- ✅ Load TRAIN.csv only (to locate 4 images)
- ✅ Access ONLY these 4 images (all TRAIN)
- ✅ NOT import validation.csv
- ✅ NOT import test.csv
- ✅ NOT access validation images
- ✅ NOT access test images
- ✅ Create no new annotations
- ✅ Train no models
- ✅ Modify no approved code

---

## EXECUTION CONSTRAINTS

**Reproducibility:**
- Fixed 4 images
- Fixed 4 experiments (no random exploration)
- Fixed preprocessing strategies (no brute-force search)
- Fixed Hough scales (3 only)
- Fixed morphology kernels (3 only)

**Time estimate:**
- Setup: ~5 minutes
- Baseline (Exp 0): ~2 seconds per image = 8 seconds
- Exp 1 (5 preprocessing methods): ~2 seconds per method per image = 40 seconds
- Exp 2 (3 scales × Hough): ~1 second per scale per image = 12 seconds
- Exp 3 (3 kernels): ~1 second per kernel per image = 12 seconds
- Exp 4 (combined): ~1 second per image = 4 seconds
- **Total execution: ~2-3 minutes**
- Report generation: ~1 minute
- **Total: ~5-10 minutes**

---

## DECISION FRAMEWORK AFTER STUDY

**IF:** 3 or 4 banks successfully detected across experiments
→ **Recommendation:** Classical pipeline has potential. Proceed to small parameter refinement.

**ELSE IF:** 2 banks successfully detected
→ **Recommendation:** Conditional improvement. Hybrid approach (classical fallback + alternative method).

**ELSE:** 0-1 banks successfully detected
→ **Recommendation:** Classical pipeline insufficient. Proceed to lightweight corner-detection model.

---

## APPROVAL CHECKLIST

Before proceeding, confirm:

- ✅ One diagnostic script only (no baseline modifications)
- ✅ Four fixed TRAIN images only
- ✅ No validation/test access
- ✅ No annotations created
- ✅ No model training
- ✅ Four predefined experiments (no random tuning)
- ✅ Approved baseline preserved for comparison
- ✅ Results measured by plausibility, not just corner count

---

**READY FOR APPROVAL**

