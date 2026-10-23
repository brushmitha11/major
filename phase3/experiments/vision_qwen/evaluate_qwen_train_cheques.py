"""
Zero-shot qwen2.5vl:7b on confirmed training cheques (verified boxes from metadata.json).

Qwen was never fine-tuned, so these cheques are valid test cases for it.
Usage: python evaluate_qwen_train_cheques.py {half|full}
  half: crops downscaled 2x (current pipeline)
  full: crops sent at native resolution
Outputs: experiments/vision_qwen/results_train_7b_{variant}.json
"""
import base64
import csv
import json
import re
import sys
from pathlib import Path

import cv2
import requests

PHASE3 = Path(__file__).resolve().parents[2]
PROJECT = PHASE3.parent
META = PHASE3 / "data" / "annotations" / "metadata.json"
TRAIN_DIR = PHASE3 / "data" / "training"
OUT_DIR = Path(__file__).resolve().parent
MODEL = "qwen2.5vl:7b"
URL = "http://127.0.0.1:11434/api/generate"
FIELDS = {"amount": "amount", "amount_words": "amount_words", "payee_name": "payee_name"}
PROMPTS = {
    "payee_name": "Read the handwritten name in this image exactly as written. Output only the name, nothing else.",
    "amount_words": "Read the handwritten amount in words exactly as written. Output only the words, nothing else.",
    "amount": "Read the handwritten amount in figures exactly as written, including commas and symbols. Output only the figures, nothing else.",
}


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def crop(img, box, pad=3):
    h, w = img.shape[:2]
    x, y, bw, bh = box
    return img[max(0, int(y * h) - pad):min(h, int((y + bh) * h) + pad),
               max(0, int(x * w) - pad):min(w, int((x + bw) * w) + pad)]


def ask(gray, prompt, variant):
    if variant == "half":
        gray = cv2.resize(gray, (max(1, gray.shape[1] // 2), max(1, gray.shape[0] // 2)))
    ok, buf = cv2.imencode(".png", gray)
    payload = {"model": MODEL, "prompt": prompt, "images": [base64.b64encode(buf).decode()],
               "stream": False, "options": {"temperature": 0}}
    r = requests.post(URL, json=payload, timeout=900)
    return r.json().get("response", "").strip()


def load_rows():
    rows = []
    for path in sorted(TRAIN_DIR.glob("training_transcriptions_batch*.csv")):
        with open(path, encoding="utf-8", newline="") as f:
            rows += list(csv.DictReader(f))
    return [r for r in rows if r["unreadable"] == "no" and r["value"] and r["field"] in FIELDS]


def main(variant):
    meta = json.loads(META.read_text(encoding="utf-8"))
    rows = load_rows()
    report = {"model": MODEL, "variant": variant, "fields": {}}
    for field in FIELDS:
        out = []
        for r in [x for x in rows if x["field"] == field]:
            uid = r["cheque_id"]
            img = cv2.imread(str(PROJECT / ("datasets/raw/idrbt/300/Cheque " + uid.split("_")[0] + ".tif")),
                             cv2.IMREAD_GRAYSCALE)
            raw = ask(crop(img, meta[uid]["fields"][field]["box"]), PROMPTS[field], variant)
            exp = r["value"].strip()
            pred = raw.strip().strip('"').strip()
            out.append({"cheque_id": uid, "expected": exp, "raw": raw, "exact": pred == exp,
                        "cer": round(lev(pred, exp) / max(1, len(exp)), 3)})
            print(variant, field, uid, "->", pred, flush=True)
        n = len(out)
        report["fields"][field] = {
            "exact": f"{sum(x['exact'] for x in out)}/{n}",
            "mean_cer": round(sum(x["cer"] for x in out) / max(1, n), 3),
            "rows": out,
        }
    (OUT_DIR / f"results_train_7b_{variant}.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", variant, flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
