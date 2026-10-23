# PHASE 3 — IMAGE QUALITY ASSESSMENT ARCHITECTURE PLAN

**Status:** Architecture design (NO CODE IMPLEMENTATION YET)

**Purpose:** Implement unified Image Quality Assessment for:
1. Dataset analysis (315 TRAIN images)
2. User-uploaded cheque quality gate

---

## 1. FILES TO CREATE/MODIFY

### Files to CREATE:

**New modules:**
- `phase3/quality/quality_result.py` — Common QualityResult structure
- `phase3/quality/quality_assessment_unified.py` — Unified quality assessment (wraps existing engine)
- `phase3/diagnostic_dataset_quality_analysis.py` — Dataset quality analysis script (TRAIN-only)
- `phase3/test_user_upload_quality_gate.py` — User-upload quality gate test

### Files to REUSE (NOT duplicate):

- `phase3/preprocessing/image_quality.py` — EXISTING approved image quality engine
  - Contains: sharpness, contrast, brightness, skew, completeness calculations
  - Will be imported and wrapped by new unified module

### Files to MODIFY:

- None (no modification to locked datasets, CSVs, or existing modules)

---

## 2. EXISTING IMAGE QUALITY MODULE REUSE

**Location:** `phase3/preprocessing/image_quality.py`

**Existing functions to reuse:**
```python
calculate_sharpness(image: np.ndarray) -> float
calculate_contrast(image: np.ndarray) -> float
calculate_brightness(image: np.ndarray) -> float
calculate_skew(image: np.ndarray) -> float
calculate_completeness(image: np.ndarray) -> float
```

**What we do:**
- Import these functions (NO duplication)
- Wrap them in a unified `QualityAssessmentEngine` class
- Convert component scores to a common `QualityResult` object
- Apply GOOD/UNCERTAIN/POOR classification
- Provide user-facing messages

---

## 3. COMMON QUALITYRESULT STRUCTURE

```python
class QualityResult:
    """Unified quality assessment result for both dataset and user contexts."""
    
    quality_score: float                    # 0.0 - 1.0
    quality_status: str                     # "GOOD", "UNCERTAIN", "POOR"
    
    component_scores: dict = {
        "sharpness": float,                 # 0.0 - 1.0
        "contrast": float,                  # 0.0 - 1.0
        "brightness": float,                # 0.0 - 1.0
        "skew": float,                      # 0.0 - 1.0
        "completeness": float,              # 0.0 - 1.0
    }
    
    issues: List[str]                       # ["The image appears blurry.", ...]
    user_message: str                       # Human-friendly summary
    recommendation: str                     # "Continue to verification" / "Re-upload"
    
    # Metadata
    image_path: Optional[str]
    context: str                            # "dataset" or "user_upload"
```

---

## 4. DATASET ANALYSIS FLOW

**Purpose:** Research analysis of 315 TRAIN images

**Process:**

```
Load train.csv
    ↓
For each of 315 TRAIN images:
    ├─ Load image
    ├─ Run Image Quality Engine
    ├─ Get QualityResult
    └─ Record result (do NOT skip poor images)
    ↓
Generate CSV report:
    image_path
    parent_id
    bank
    label
    forgery_type
    sharpness
    contrast
    brightness
    skew
    completeness
    quality_score
    quality_status
    issues
    ↓
Generate statistics:
    - % GOOD images per bank
    - % UNCERTAIN images per bank
    - % POOR images per bank
    - Common quality issues
    - Sharpness distribution
    - Contrast distribution
    - etc.
    ↓
Report findings (no image exclusion)
```

**Key point:** Do NOT exclude or stop on poor images. This is research analysis.

**Output:**
- CSV: `phase3/datasets_quality_report.csv`
- Summary statistics printed to console

---

## 5. USER-UPLOAD QUALITY GATE FLOW

**Purpose:** Quality gate for user-uploaded cheque images

**Process:**

```
User uploads image
    ↓
Image Quality Engine
    ├─ Load image
    ├─ Calculate components
    └─ Get QualityResult
    ↓
Quality Gate Decision:
    ├─ If GOOD:
    │   └─ "Image Quality: Good ✅"
    │       "Proceeding with verification..."
    │       → Continue to cheque verification
    │
    ├─ If UNCERTAIN:
    │   └─ "Image Quality: Uncertain ⚠️"
    │       "The image quality may affect reliability..."
    │       → STOP. Ask user to re-upload
    │
    └─ If POOR:
        └─ "Image Quality: Poor ⚠️"
            "Problems detected: [list issues]"
            → STOP. Ask user to re-upload
```

**Key point:** UNCERTAIN and POOR prevent verification pipeline continuation.

---

## 6. GOOD / UNCERTAIN / POOR DETERMINATION

**Thresholds (PROVISIONAL, CONFIGURABLE):**

```python
PROVISIONAL_GOOD_THRESHOLD = 0.65          # quality_score >= 0.65
PROVISIONAL_UNCERTAIN_LOWER = 0.50         # 0.50 <= quality_score < 0.65
# POOR: quality_score < 0.50

STATUS LOGIC:
    if quality_score >= 0.65:
        status = "GOOD"
    elif quality_score >= 0.50:
        status = "UNCERTAIN"
    else:
        status = "POOR"
```

**Composite quality_score:**

```python
quality_score = (
    0.20 * sharpness +           # 20%
    0.20 * contrast +            # 20%
    0.20 * brightness +          # 20%
    0.15 * (1.0 - skew_pct) +    # 15% (inverse: lower skew = higher score)
    0.25 * completeness          # 25%
)

# Thresholds are PROVISIONAL and NOT scientifically validated
# Must remain configurable for future validation/tuning
```

---

## 7. CONFIGURABLE THRESHOLD MECHANISM

**Implementation:**

```python
class QualityGateConfig:
    """Configurable quality thresholds (PROVISIONAL, FOR RESEARCH)."""
    
    # Thresholds (NOT final, subject to change)
    good_threshold: float = 0.65
    uncertain_threshold: float = 0.50
    
    # Component weights
    weights: dict = {
        "sharpness": 0.20,
        "contrast": 0.20,
        "brightness": 0.20,
        "skew": 0.15,
        "completeness": 0.25,
    }
    
    @classmethod
    def from_file(cls, config_path: str):
        """Load from JSON config for easy tuning."""
        pass
    
    @classmethod
    def default(cls):
        """Current provisional defaults."""
        return cls()
```

**Why configurable:**
- Current thresholds are PROVISIONAL
- Future validation may require tuning
- Different cheque types may need different thresholds
- Research goal is to eventually validate these values

---

## 8. HOW POOR/UNCERTAIN PREVENT VERIFICATION

**Architecture:**

```python
def process_user_uploaded_cheque(image_path: str) -> VerificationResult:
    """Main verification pipeline with quality gate."""
    
    # Step 1: Quality assessment
    quality_result = quality_engine.assess(image_path)
    
    # Step 2: Quality gate
    if quality_result.quality_status in ["POOR", "UNCERTAIN"]:
        # STOP pipeline
        return VerificationResult(
            status="QUALITY_GATE_FAILED",
            message=quality_result.user_message,
            recommendation=quality_result.recommendation
        )
    
    # Step 3: Continue only if GOOD
    # (Cheque registration, field localization, etc.)
    return proceed_with_verification(image_path)
```

**User sees:**
- Quality gate message (not technical scores)
- Reason for rejection (if applicable)
- Instruction to re-upload

---

## 9. USER-FACING MESSAGES

**Message generation (NOT raw scores):**

```python
def generate_user_message(quality_result: QualityResult) -> str:
    """Convert QualityResult to user-friendly message."""
    
    if quality_result.quality_status == "GOOD":
        return (
            "Image Quality: Good ✅\n\n"
            "The cheque image is clear enough for automated verification.\n\n"
            "Proceeding with verification..."
        )
    
    elif quality_result.quality_status == "UNCERTAIN":
        return (
            "Image Quality: Uncertain ⚠️\n\n"
            "The image quality may affect verification reliability.\n\n"
            "Please re-upload a clearer image before continuing."
        )
    
    elif quality_result.quality_status == "POOR":
        issues_str = "\n".join(f"• {issue}" for issue in quality_result.issues)
        return (
            "Image Quality: Poor ⚠️\n\n"
            "We cannot reliably process this cheque image.\n\n"
            "Problems detected:\n"
            f"{issues_str}\n\n"
            "Please re-upload a clear, complete image of the cheque."
        )
```

**Issue message mapping:**

```python
ISSUE_MESSAGES = {
    "low_sharpness": "The image appears blurry.",
    "poor_contrast": "The cheque details may be difficult to read due to low contrast.",
    "poor_brightness": "The image brightness may make cheque details difficult to read.",
    "excessive_skew": "The cheque appears tilted. Please photograph it straight-on.",
    "incomplete_cheque": "The complete cheque may not be visible.",
}
```

---

## 10. EXACT DATASET DIAGNOSTIC COMMAND

```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque
python phase3/diagnostic_dataset_quality_analysis.py
```

**Output:**
- Progress: "Analyzing TRAIN image 1/315..."
- CSV file: `phase3/datasets_quality_report.csv`
- Console report:
  - Statistics by bank
  - Quality distribution
  - Common issues
  - Example images per quality level

**Duration:** ~2-3 minutes (315 images, ~400-600ms per image)

---

## 11. EXACT USER-UPLOAD QUALITY GATE TEST COMMAND

```bash
cd C:\Users\Rushmitha\OneDrive\Desktop\cheque
python phase3/test_user_upload_quality_gate.py --image <path_to_test_image>
```

**Example usage:**

```bash
# Test with a TRAIN image
python phase3/test_user_upload_quality_gate.py --image datasets/raw/idrbt/300/Cheque 309137.tif

# Test with a low-quality image
python phase3/test_user_upload_quality_gate.py --image test_images/blurry.jpg
```

**Output:**
- User message (as it would appear to real user)
- Quality scores (for diagnostic purposes)
- Component breakdown
- Gate result (PASS/FAIL)

---

## 12. DATA PROTECTION CONFIRMATION

**For dataset analysis:**
- ✅ TRAIN-only (all 315 images from train.csv)
- ❌ No validation.csv access
- ❌ No test.csv access
- ❌ No validation images accessed
- ❌ No TEST images accessed
- ❌ No modification to dataset images
- ❌ No modification to CSV files
- ✅ Results recorded in new report CSV (separate file)

**For user upload:**
- ✅ Quality assessment on uploaded image
- ❌ Uploaded images NOT added to dataset automatically
- ❌ Locked dataset splits NOT modified
- ❌ No training on user images
- ❌ No annotation creation

---

## ARCHITECTURE SUMMARY

```
┌─────────────────────────────────────────────────────────────┐
│                  Image Quality Engine                        │
│        (wraps existing phase3/preprocessing/image_quality.py)│
│                                                              │
│  Input: Image (file path or numpy array)                    │
│  Output: QualityResult (structured object)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                ↓                       ↓
        Dataset Analysis          User Upload Gate
        (Research)                 (Verification)
                ↓                       ↓
        Record Results          GOOD/UNCERTAIN/POOR
        Generate Report         └─ GOOD → Continue
        Statistics                 UNCERTAIN → Re-upload
                                  POOR → Re-upload
```

---

## KEY DESIGN DECISIONS

1. **Single engine, two contexts:**
   - Same QualityResult structure for both
   - Dataset records everything (no filtering)
   - User gate stops on UNCERTAIN/POOR

2. **Configurable thresholds:**
   - Current values are PROVISIONAL
   - Stored in config object
   - Can be tuned via JSON config file
   - NOT hard-coded as final

3. **User-friendly messages:**
   - No raw scores displayed to users
   - Issues described in plain language
   - Clear recommendation (re-upload)
   - Professional tone

4. **No duplication:**
   - Single source of truth: existing image_quality.py
   - Unified QualityResult structure
   - Single gate logic

5. **Data protection:**
   - TRAIN-only for dataset analysis
   - No modification to locked datasets
   - Uploaded images not stored in research set

---

## IMPLEMENTATION CHECKLIST

Before writing code:

- ✅ Files to create: 4 new modules
- ✅ Files to reuse: image_quality.py (existing)
- ✅ Files to preserve: locked datasets, CSVs
- ✅ Common structure: QualityResult class
- ✅ Dataset flow: analyze all, record all
- ✅ User flow: GOOD/UNCERTAIN/POOR gates
- ✅ Threshold mechanism: configurable, provisional
- ✅ Messages: user-friendly, issue-specific
- ✅ Prevention logic: POOR/UNCERTAIN stop verification
- ✅ Commands: dataset analysis + user test
- ✅ Data protection: TRAIN-only, no modifications

---

**READY FOR ARCHITECTURE APPROVAL**

