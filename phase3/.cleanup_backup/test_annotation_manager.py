import tempfile, json, sys, math
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from data.annotations.annotation_manager import AnnotationManager, AnnotationValidator, ImageAnnotation, FieldAnnotation

print("\n" + "=" * 80)
print("COMPREHENSIVE UNIT TEST SUITE")
print("=" * 80)

# TEST 1: Persistence
print("\n[TEST 1] Save and reload metadata")
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        manager = AnnotationManager(output_dir=tmpdir, train_csv="../datasets/splits/train.csv")
        sample_image = list(manager.train_images.keys())[0]
        sample_data = manager.train_images[sample_image]
        ann = manager.create_annotation(sample_image, "persist_001", sample_data['parent_id'], sample_data['bank'])
        manager.register_annotation(ann)
        manager2 = AnnotationManager(output_dir=tmpdir, train_csv="../datasets/splits/train.csv")
        assert "persist_001" in manager2.metadata
        print("  PASS: Persistence works")
    except Exception as e:
        print(f"  FAIL: {e}")

# TEST 2: YOLO generation
print("\n[TEST 2] YOLO label generation")
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        manager = AnnotationManager(output_dir=tmpdir, train_csv="../datasets/splits/train.csv")
        sample_image = list(manager.train_images.keys())[0]
        sample_data = manager.train_images[sample_image]
        ann = manager.create_annotation(sample_image, "yolo_001", sample_data['parent_id'], sample_data['bank'])
        ann.fields['cheque_number'] = FieldAnnotation('cheque_number', 'detected', box=[0.8, 0.05, 0.35, 0.1], verified=True)
        for fname in ['bank_name', 'account_number', 'date', 'payee_name', 'amount', 'signature', 'micr_code']:
            ann.fields[fname].status = 'absent'
        manager.register_annotation(ann)
        yolo_file = Path(tmpdir) / "yolo/train/yolo_001.txt"
        assert yolo_file.exists()
        lines = yolo_file.read_text().strip().split('\n')
        assert len(lines) == 1
        print("  PASS: YOLO generation works")
    except Exception as e:
        print(f"  FAIL: {e}")

# TEST 3: Draft resume
print("\n[TEST 3] Draft save and resume")
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        manager = AnnotationManager(output_dir=tmpdir, train_csv="../datasets/splits/train.csv")
        sample_image = list(manager.train_images.keys())[0]
        sample_data = manager.train_images[sample_image]
        ann = manager.create_annotation(sample_image, "draft_001", sample_data['parent_id'], sample_data['bank'])
        manager.register_annotation(ann)
        ann.fields['cheque_number'].status = 'detected'
        ann.fields['cheque_number'].box = [0.8, 0.05, 0.35, 0.1]
        ann.fields['cheque_number'].verified = True
        manager.save_draft(ann)
        manager2 = AnnotationManager(output_dir=tmpdir, train_csv="../datasets/splits/train.csv")
        resumed = manager2.get_annotation("draft_001")
        assert resumed.fields['cheque_number'].status == 'detected'
        print("  PASS: Draft resume works")
    except Exception as e:
        print(f"  FAIL: {e}")

# TEST 4: Validation edge cases
print("\n[TEST 4] Validation - NaN, infinity, boolean, bounds")
manager = AnnotationManager(output_dir=".", train_csv="../datasets/splits/train.csv")
sample_image = list(manager.train_images.keys())[0]
test_cases = [
    ("NaN", [float('nan'), 0.5, 0.2, 0.1], False),
    ("Infinity", [float('inf'), 0.5, 0.2, 0.1], False),
    ("Boolean", [True, 0.5, 0.2, 0.1], False),
    ("Negative width", [0.5, 0.5, -0.2, 0.1], False),
    ("Zero height", [0.5, 0.5, 0.2, 0], False),
    ("Left out", [0.1, 0.5, 0.3, 0.1], False),
    ("Right out", [0.9, 0.5, 0.3, 0.1], False),
    ("Valid", [0.5, 0.5, 0.2, 0.1], True),
]
passed = 0
for name, box, should_be_valid in test_cases:
    try:
        fields = {f: FieldAnnotation(f, 'absent') for f in manager.ALL_FIELDS}
        fields['cheque_number'] = FieldAnnotation('cheque_number', 'detected', box=box, verified=True)
        ann = ImageAnnotation("test", sample_image, "123", "BANK", "train", "complete", fields)
        is_valid, errors = AnnotationValidator.validate_annotation(ann)
        if is_valid == should_be_valid:
            passed += 1
    except:
        pass
print(f"  {passed}/{len(test_cases)} validation tests passed")

# TEST 5: All 8 fields required
print("\n[TEST 5] All 8 fields required")
try:
    for missing in manager.ALL_FIELDS:
        fields = {f: FieldAnnotation(f, 'absent') for f in manager.ALL_FIELDS if f != missing}
        ann = ImageAnnotation("test", sample_image, "123", "BANK", "train", "complete", fields)
        is_valid, _ = AnnotationValidator.validate_annotation(ann)
        assert not is_valid
    print("  PASS: All 8 fields required")
except Exception as e:
    print(f"  FAIL: {e}")

# TEST 6: Duplicate ID
print("\n[TEST 6] Duplicate ID rejection")
with tempfile.TemporaryDirectory() as tmpdir:
    try:
        manager = AnnotationManager(output_dir=tmpdir, train_csv="../datasets/splits/train.csv")
        sample_image = list(manager.train_images.keys())[0]
        sample_data = manager.train_images[sample_image]
        ann1 = manager.create_annotation(sample_image, "dup_001", sample_data['parent_id'], sample_data['bank'])
        manager.register_annotation(ann1)
        ann2 = manager.create_annotation(sample_image, "dup_001", sample_data['parent_id'], sample_data['bank'])
        assert ann2 is None
        print("  PASS: Duplicate IDs rejected")
    except Exception as e:
        print(f"  FAIL: {e}")

print("\n" + "=" * 80)
print("TESTS COMPLETED")
print("=" * 80)
