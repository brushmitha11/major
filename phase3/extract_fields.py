"""
Extract text from the labeled training cheques.

Printed fields -> PaddleOCR. Handwritten fields -> TrOCR. Signature is not read as text.
Reads phase3/data/annotations/metadata.json (read-only) and the training split only.
Writes phase3/data/extraction/extraction_results.json.
"""
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_CSV = PROJECT_ROOT / "datasets" / "splits" / "train.csv"
METADATA = PROJECT_ROOT / "phase3" / "data" / "annotations" / "metadata.json"
OUT = PROJECT_ROOT / "phase3" / "data" / "extraction" / "extraction_results.json"
OUT_PRINTED = PROJECT_ROOT / "phase3" / "data" / "extraction" / "extraction_printed.json"
OUT_HANDWRITTEN = PROJECT_ROOT / "phase3" / "data" / "extraction" / "extraction_handwritten.json"
printed_only = "--printed" in sys.argv
handwritten_only = "--handwritten" in sys.argv

PRINTED = ["cheque_number", "bank_name", "account_number", "ifsc_code", "micr_code"]
HANDWRITTEN = ["date", "amount", "amount_words", "payee_name"]
NOT_TEXT = ["signature"]


def train_uids():
    uids = {}
    with open(TRAIN_CSV, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["label"] == "reference":
                uids[f"{Path(r['image_path']).stem.split()[-1]}_reference"] = r["image_path"]
    return uids


def crop(img, box):
    h, w = img.shape[:2]
    x, y, bw, bh = box
    x0, y0 = max(0, int(x * w)), max(0, int(y * h))
    x1, y1 = min(w, int((x + bw) * w)), min(h, int((y + bh) * h))
    return img[y0:y1, x0:x1]


def check(field, text):
    t = text.replace(" ", "")
    if field == "ifsc_code":
        fixed = re.sub(r"^([A-Z]{4})O", r"\g<1>0", t.upper())
        ok = bool(re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", fixed))
        return ok, fixed
    if field == "micr_code":
        digits = re.sub(r"\D", "", t)
        return len(digits) >= 9, digits
    if field == "account_number":
        digits = re.sub(r"\D", "", t)
        return 8 <= len(digits) <= 20, digits
    if field == "cheque_number":
        digits = re.sub(r"\D", "", t)
        return 6 <= len(digits) <= 10, digits
    if field == "date":
        digits = re.sub(r"[^0-9]", "", t)
        for fmt in ("%d%m%Y",):
            try:
                if len(digits) == 8:
                    datetime.strptime(digits, fmt)
                    return True, digits
            except ValueError:
                pass
        return False, digits
    if field == "amount":
        digits = re.sub(r"[^0-9.]", "", t)
        return bool(digits), digits
    return bool(text.strip()), text.strip()


def main():
    from paddleocr import PaddleOCR
    import torch
    from PIL import Image
    from transformers import TrOCRProcessor, VisionEncoderDecoderModel

    meta = json.loads(METADATA.read_text(encoding="utf-8"))
    train = train_uids()
    targets = sorted(u for u in meta if u in train and meta[u]["status"] == "complete")

    if handwritten_only:
        ocr = None
    else:
        ocr = PaddleOCR(lang="en", use_doc_orientation_classify=False,
                        use_doc_unwarping=False, use_textline_orientation=False, enable_mkldnn=False)
    if printed_only:
        proc = model = None
    else:
        proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
        model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten").eval()
    out_path = OUT_PRINTED if printed_only else OUT_HANDWRITTEN if handwritten_only else OUT

    results = {}
    for n, uid in enumerate(targets, 1):
        image_path = PROJECT_ROOT / train[uid]
        img = cv2.imread(str(image_path))
        fields = {}
        for field, v in meta[uid]["fields"].items():
            if v["status"] != "detected" or not v["box"]:
                fields[field] = {"status": v["status"], "text": None}
                continue
            part = crop(img, v["box"])
            if field in NOT_TEXT:
                fields[field] = {"status": "detected", "text": None, "note": "signature not read as text"}
                continue
            if handwritten_only and field in PRINTED:
                fields[field] = {"status": "detected", "text": None, "note": "printed field skipped"}
                continue
            if field in PRINTED:
                res = ocr.predict(part)
                texts, scores = [], []
                for r in res:
                    texts += list(r.get("rec_texts", []))
                    scores += [float(s) for s in r.get("rec_scores", [])]
                text = " ".join(texts)
                conf = round(float(np.mean(scores)), 3) if scores else None
                engine = "paddleocr"
            elif printed_only:
                fields[field] = {"status": "detected", "text": None, "note": "handwritten field skipped"}
                continue
            else:
                rgb = cv2.cvtColor(part, cv2.COLOR_BGR2RGB)
                pix = proc(images=Image.fromarray(rgb), return_tensors="pt").pixel_values
                with torch.no_grad():
                    ids = model.generate(pix, max_new_tokens=64)
                text = proc.batch_decode(ids, skip_special_tokens=True)[0]
                conf = None
                engine = "trocr"
            ok, normalised = check(field, text)
            fields[field] = {"status": "detected", "engine": engine, "text": text,
                             "normalised": normalised, "confidence": conf, "format_ok": ok}
        results[uid] = {"image_path": train[uid], "fields": fields}
        print(f"[{n}/{len(targets)}] {uid} done", flush=True)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_path, "cheques:", len(results), flush=True)


if __name__ == "__main__":
    sys.exit(main())
