"""
Propagate field boxes from one labeled template cheque to other cheques of the same bank.

Output is proposals only: saved to phase3/data/pseudo_labels/, marked is_verified=False.
Never writes to phase3/data/annotations/ or datasets/.

Only training-split references are processed. Validation and test cheques are never used.
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_CSV = PROJECT_ROOT / "datasets" / "splits" / "train.csv"
ANNOTATIONS_FILE = PROJECT_ROOT / "phase3" / "data" / "annotations" / "metadata.json"

MIN_INLIERS = 40
MIN_INLIER_RATIO = 0.25
AREA_RATIO_RANGE = (0.8, 1.25)


def load_image(path):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"cannot read {path}")
    return img


def match_homography(template_gray, target_gray, nfeatures=5000):
    orb = cv2.ORB_create(nfeatures=nfeatures)
    kp_t, des_t = orb.detectAndCompute(template_gray, None)
    kp_s, des_s = orb.detectAndCompute(target_gray, None)
    if des_t is None or des_s is None:
        return None, 0, 0
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING)
    knn = matcher.knnMatch(des_t, des_s, k=2)
    good = [m for pair in knn if len(pair) == 2 for m, n in [pair] if m.distance < 0.75 * n.distance]
    if len(good) < 4:
        return None, len(good), 0
    src = np.float32([kp_t[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
    dst = np.float32([kp_s[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if H is None:
        return None, len(good), 0
    inliers = int(mask.sum())
    return H, len(good), inliers


def map_box(norm_box, H, t_w, t_h, s_w, s_h):
    x, y, w, h = norm_box
    corners = np.float32([
        [x * t_w, y * t_h],
        [(x + w) * t_w, y * t_h],
        [(x + w) * t_w, (y + h) * t_h],
        [x * t_w, (y + h) * t_h],
    ]).reshape(-1, 1, 2)
    mapped = cv2.perspectiveTransform(corners, H).reshape(-1, 2)
    xs, ys = mapped[:, 0], mapped[:, 1]
    x0, x1 = max(0.0, xs.min()), min(float(s_w), xs.max())
    y0, y1 = max(0.0, ys.min()), min(float(s_h), ys.max())
    if x1 <= x0 or y1 <= y0:
        return None, "mapped box outside target image"
    orig_area = (w * t_w) * (h * t_h)
    quad_area = cv2.contourArea(mapped.astype(np.float32))
    ratio = quad_area / orig_area if orig_area > 0 else 0
    flag = None
    if not (AREA_RATIO_RANGE[0] <= ratio <= AREA_RATIO_RANGE[1]):
        flag = f"area ratio {ratio:.2f} outside {AREA_RATIO_RANGE}"
    box = [x0 / s_w, y0 / s_h, (x1 - x0) / s_w, (y1 - y0) / s_h]
    return {"box": [round(v, 6) for v in box], "flag": flag}, None


def align_target(template_gray, target_gray, template_boxes):
    t_h, t_w = template_gray.shape[:2]
    s_h, s_w = target_gray.shape[:2]
    H, n_good, n_inl = match_homography(template_gray, target_gray)
    ratio = n_inl / n_good if n_good else 0
    result = {"matches": n_good, "inliers": n_inl, "inlier_ratio": round(ratio, 3)}
    if H is None or n_inl < MIN_INLIERS or ratio < MIN_INLIER_RATIO:
        result["status"] = "alignment_failed"
        result["fields"] = {}
        return result
    result["status"] = "aligned"
    fields = {}
    for field, norm_box in template_boxes.items():
        mapped, err = map_box(norm_box, H, t_w, t_h, s_w, s_h)
        if err:
            fields[field] = {"box": None, "error": err}
            continue
        fields[field] = {
            "box": mapped["box"],
            "is_verified": False,
            "source": "alignment_propagation",
            "flag": mapped["flag"],
        }
    result["fields"] = fields
    return result


def load_template(template_uid):
    data = json.loads(ANNOTATIONS_FILE.read_text(encoding="utf-8"))
    ann = data.get(template_uid)
    if not ann:
        raise SystemExit(f"No annotation for template {template_uid} in {ANNOTATIONS_FILE}")
    if ann.get("status") != "complete":
        raise SystemExit(f"Template {template_uid} must be marked complete before propagation")
    boxes = {}
    for field, f in ann.get("fields", {}).items():
        if f.get("status") == "detected" and f.get("box"):
            boxes[field] = f["box"]
    return ann["image_path"], boxes


def bank_train_references(bank):
    with open(TRAIN_CSV, encoding="utf-8", newline="") as f:
        return [r for r in csv.DictReader(f)
                if r["bank"] == bank and r["label"] == "reference"]


def output_file(bank):
    slug = bank.split()[0].lower()
    name = "alignment_proposals.json" if slug == "axis" else f"alignment_proposals_{slug}.json"
    return PROJECT_ROOT / "phase3" / "data" / "pseudo_labels" / name


def run(template_uid, bank):
    template_rel, template_boxes = load_template(template_uid)
    if not template_boxes:
        raise SystemExit("Template has no detected boxes to propagate")
    template_gray = load_image(PROJECT_ROOT / template_rel)

    out = {}
    counts = {"aligned": 0, "alignment_failed": 0, "flagged_fields": 0}
    for row in bank_train_references(bank):
        uid = f"{Path(row['image_path']).stem.split()[-1]}_reference"
        if uid == template_uid:
            continue
        target_gray = cv2.imread(str(PROJECT_ROOT / row["image_path"]), cv2.IMREAD_GRAYSCALE)
        if target_gray is None:
            out[uid] = {"status": "unreadable", "error": "cannot read image"}
            counts["alignment_failed"] += 1
            continue
        res = align_target(template_gray, target_gray, template_boxes)
        res["image_path"] = row["image_path"]
        res["template_uid"] = template_uid
        res["is_verified"] = False
        counts[res["status"]] += 1
        counts["flagged_fields"] += sum(1 for f in res["fields"].values() if f.get("flag"))
        out[uid] = res

    out_path = output_file(bank)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({"template": template_uid, "bank": bank, "targets": len(out), **counts,
                      "output": str(out_path)}, indent=2))


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        raise SystemExit("usage: python align_proposals.py <template_uid> [bank]")
    run(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else "AXIS BANK")
