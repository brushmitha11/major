"""
Tag the approved training images and decide detector-training eligibility.

Reads datasets/splits/train.csv (read-only) and writes:
  phase3/data/dataset_tags/image_tags.csv
  phase3/data/dataset_tags/tagging_summary.json

Does not modify train.csv, source images, or any annotation files.
"""
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_CSV = PROJECT_ROOT / "datasets" / "splits" / "train.csv"
OUT_DIR = PROJECT_ROOT / "phase3" / "data" / "dataset_tags"

LOW_CONTRAST_STD = 25.0  # heuristic threshold on grayscale std; reviewed against the distribution below


def uid_for(image_path: str, parent_id: str) -> str:
    stem = Path(image_path).stem
    if "_forgery" in stem.lower():
        return stem
    return f"{parent_id}_reference"


def main():
    with open(TRAIN_CSV, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))

    problems = []
    seen_paths = set()
    references = {}
    for row in rows:
        p = row["image_path"]
        if p in seen_paths:
            problems.append(f"duplicate image_path in train.csv: {p}")
        seen_paths.add(p)
        if row["label"] == "reference":
            if row["parent_id"] in references:
                problems.append(f"multiple references for parent {row['parent_id']}")
            references[row["parent_id"]] = row

    tags = []
    stats_std = []
    for row in rows:
        image_path = row["image_path"]
        parent_id = row["parent_id"]
        label = row["label"]
        full = PROJECT_ROOT / image_path

        rec = {
            "uid": uid_for(image_path, parent_id),
            "image_path": image_path,
            "parent_id": parent_id,
            "bank": row["bank"],
            "label": label,
            "forgery_type": row["forgery_type"],
            "source_type": "real_reference" if label == "reference" else "synthetic_forgery",
            "source_image": row["source_image"],
            "file_exists": full.exists(),
            "decodable": False,
            "width": "",
            "height": "",
            "grey_std": "",
            "low_contrast": "",
            "parent_consistent": "",
            "field_label_status": "unlabeled",
            "detector_training_eligible": False,
            "eligibility_reason": "",
        }

        if label == "reference":
            rec["parent_consistent"] = True
        else:
            ref = references.get(parent_id)
            ok = ref is not None and ref["image_path"] == row["source_image"] and ref["bank"] == row["bank"]
            rec["parent_consistent"] = ok
            if not ok:
                problems.append(f"forgery {image_path} does not match its reference row")

        if not rec["file_exists"]:
            rec["eligibility_reason"] = "image file missing"
            tags.append(rec)
            continue

        img = cv2.imread(str(full), cv2.IMREAD_GRAYSCALE)
        if img is None:
            rec["eligibility_reason"] = "image cannot be decoded"
            tags.append(rec)
            continue

        h, w = img.shape[:2]
        std = float(np.std(img))
        rec.update({
            "decodable": True,
            "width": w,
            "height": h,
            "grey_std": round(std, 2),
            "low_contrast": std < LOW_CONTRAST_STD,
        })
        stats_std.append(std)

        if label != "reference":
            rec["eligibility_reason"] = "unverified synthetic forgery: field edits make its boxes untrustworthy"
        elif not rec["parent_consistent"]:
            rec["eligibility_reason"] = "reference row inconsistent"
        elif rec["low_contrast"]:
            rec["eligibility_reason"] = "real reference, low contrast: review before labeling"
            rec["detector_training_eligible"] = False
        else:
            rec["eligibility_reason"] = "real reference: eligible for manual field labeling"
            rec["detector_training_eligible"] = True
        tags.append(rec)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = list(tags[0].keys())
    with open(OUT_DIR / "image_tags.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(tags)

    eligible = [t for t in tags if t["detector_training_eligible"]]
    excluded_reasons = Counter(t["eligibility_reason"] for t in tags if not t["detector_training_eligible"])
    bank_counts = Counter(t["bank"] for t in tags)
    eligible_bank = Counter(t["bank"] for t in eligible)
    parent_groups = defaultdict(list)
    for t in tags:
        parent_groups[t["parent_id"]].append(t["uid"])

    summary = {
        "source": "datasets/splits/train.csv (read-only)",
        "total_rows": len(rows),
        "unique_parents": len(parent_groups),
        "real_references": sum(1 for t in tags if t["source_type"] == "real_reference"),
        "synthetic_forgeries": sum(1 for t in tags if t["source_type"] == "synthetic_forgery"),
        "decodable": sum(1 for t in tags if t["decodable"]),
        "detector_training_eligible": len(eligible),
        "excluded_reasons": dict(excluded_reasons),
        "bank_counts_all": dict(bank_counts),
        "bank_counts_eligible": dict(eligible_bank),
        "grey_std_min": round(min(stats_std), 2) if stats_std else None,
        "grey_std_median": round(float(np.median(stats_std)), 2) if stats_std else None,
        "grey_std_max": round(max(stats_std), 2) if stats_std else None,
        "low_contrast_threshold_heuristic": LOW_CONTRAST_STD,
        "low_contrast_count": sum(1 for t in tags if t["low_contrast"] is True),
        "consistency_problems": problems,
        "notes": [
            "No field boxes are verified yet; field_label_status is 'unlabeled' for all images.",
            "Eligibility means eligible for manual labeling, not for training with labels.",
            "The contrast threshold is a heuristic and has not been validated against field-readability labels.",
        ],
    }
    with open(OUT_DIR / "tagging_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
