"""
Improved handwritten extraction (v2) for the labeled training cheques.

Changes from v1 (extract_fields.py):
- Date: split into the 8 digit cells of the printed date box, recognised one cell at a time.
- Wide lines (amount in words, payee): split at word gaps into chunks of bounded aspect ratio.
- Every chunk is padded to a square instead of being squashed by the TrOCR processor.
- Each result carries a confidence (geometric mean token probability) and a review flag.

Original outputs are not modified. Writes phase3/data/extraction/extraction_handwritten_v2.json.
"""
import csv
import json
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAIN_CSV = PROJECT_ROOT / "datasets" / "splits" / "train.csv"
METADATA = PROJECT_ROOT / "phase3" / "data" / "annotations" / "metadata.json"
OUT = PROJECT_ROOT / "phase3" / "data" / "extraction" / "extraction_handwritten_v2.json"

HANDWRITTEN = ["date", "amount", "amount_words", "payee_name"]
MAX_ASPECT = 2.5
REVIEW_PROB = 0.6


def train_reference_paths():
    out = {}
    with open(TRAIN_CSV, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["label"] == "reference":
                out[f"{Path(r['image_path']).stem.split()[-1]}_reference"] = r["image_path"]
    return out


def crop_box(img, box, pad=3):
    h, w = img.shape[:2]
    x, y, bw, bh = box
    x0, y0 = max(0, int(x * w) - pad), max(0, int(y * h) - pad)
    x1, y1 = min(w, int((x + bw) * w) + pad), min(h, int((y + bh) * h) + pad)
    return img[y0:y1, x0:x1]


def clean_line(gray):
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    w = ink.shape[1]
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(15, w // 6), 1))
    lines = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    ink = cv2.subtract(ink, lines)
    rows = np.where(ink.sum(axis=1) / 255.0 > 0.01 * w)[0]
    if rows.size == 0:
        return gray
    top, bottom = max(0, rows[0] - 4), min(gray.shape[0], rows[-1] + 5)
    cleaned = np.where(ink[top:bottom] > 0, gray[top:bottom] * 0 + 40, 255).astype(np.uint8)
    return cleaned


def pad_to_square(gray):
    h, w = gray.shape[:2]
    side = max(h, w) + 20
    canvas = np.full((side, side), 255, np.uint8)
    y0, x0 = (side - h) // 2, (side - w) // 2
    canvas[y0:y0 + h, x0:x0 + w] = gray
    return Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_GRAY2RGB))


def word_gaps(gray):
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    profile = ink.sum(axis=0) / 255.0
    h = gray.shape[0]
    thresh = max(1.0, 0.04 * h)
    blank = profile < thresh
    gaps, start = [], None
    for i, b in enumerate(blank):
        if b and start is None:
            start = i
        elif not b and start is not None:
            if i - start >= 0.3 * h:
                gaps.append((start + i) // 2)
            start = None
    return gaps


def chunk_line(gray):
    h, w = gray.shape[:2]
    if w <= MAX_ASPECT * 2 * h:
        return [gray]
    gaps = word_gaps(gray)
    cuts, last = [], 0
    for g in gaps:
        if g - last >= MAX_ASPECT * h:
            cuts.append(g)
            last = g
    bounds = [0] + cuts + [w]
    chunks = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        if b - a > MAX_ASPECT * 2 * h:
            step = int(MAX_ASPECT * h)
            for s in range(a, b, step):
                chunks.append(gray[:, s:min(b, s + step)])
        else:
            chunks.append(gray[:, a:b])
    return [c for c in chunks if c.shape[1] > 4]


def recognise(proc, model, pil_images, bad_words_ids=None):
    pix = proc(images=pil_images, return_tensors="pt").pixel_values
    with torch.no_grad():
        out = model.generate(pix, max_new_tokens=48, output_scores=True,
                             return_dict_in_generate=True, bad_words_ids=bad_words_ids)
    texts = proc.batch_decode(out.sequences, skip_special_tokens=True)
    trans = model.compute_transition_scores(out.sequences, out.scores, normalize_logits=True)
    probs = []
    for row in trans:
        vals = [float(torch.exp(v)) for v in row if torch.isfinite(v)]
        probs.append(float(np.exp(np.mean(np.log(np.clip(vals, 1e-6, 1))))) if vals else 0.0)
    return [t.strip() for t in texts], probs


def recognise_field(proc, model, gray_crop, field):
    if field == "date":
        h, w = gray_crop.shape[:2]
        cell_w = w / 8.0
        cells = []
        for i in range(8):
            a, b = int(i * cell_w) + 4, int((i + 1) * cell_w) - 4
            cells.append(gray_crop[:, a:b])
        texts, probs = recognise(proc, model, [pad_to_square(c) for c in cells])
        digits = "".join(ch for t in texts for ch in t if ch.isdigit())
        return {"chunks": texts, "text": digits, "probs": probs}
    chunks = chunk_line(gray_crop) if field != "amount" else [gray_crop]
    texts, probs = recognise(proc, model, [pad_to_square(c) for c in chunks])
    return {"chunks": texts, "text": " ".join(t for t in texts if t), "probs": probs}


def main():
    meta = json.loads(METADATA.read_text(encoding="utf-8"))
    refs = train_reference_paths()
    targets = sorted(u for u in meta if u in refs and meta[u]["status"] == "complete")

    proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten").eval()

    results = {}
    for n, uid in enumerate(targets, 1):
        img = cv2.imread(str(PROJECT_ROOT / refs[uid]), cv2.IMREAD_GRAYSCALE)
        fields = {}
        for field in HANDWRITTEN:
            box = meta[uid]["fields"][field]["box"]
            gray = crop_box(img, box)
            r = recognise_field(proc, model, gray, field)
            prob = float(np.mean(r["probs"])) if r["probs"] else 0.0
            fields[field] = {
                "text": r["text"],
                "chunks": r["chunks"],
                "chunk_probs": [round(p, 3) for p in r["probs"]],
                "confidence": round(prob, 3),
                "review": prob < REVIEW_PROB or not r["text"],
            }
        results[uid] = {"image_path": refs[uid], "fields": fields}
        print(f"[{n}/{len(targets)}] {uid} done", flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, "cheques:", len(results), flush=True)


if __name__ == "__main__":
    sys.exit(main())
