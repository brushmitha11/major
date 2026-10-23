"""
Evaluate qwen2.5vl:3b (served by local Ollama) on the held-out cheques for the three text fields.

Inputs: confirmed held-out values (ground_truth_template.csv) and candidate boxes (unverified).
Outputs: experiments/vision_qwen/results.json with raw outputs, exact match, CER, WER, invalid outputs.
The held-out cheques were not used for any training here.
"""
import base64
import csv
import json
import re
from pathlib import Path

import cv2
import requests

PHASE3 = Path(__file__).resolve().parents[2]
PROJECT = PHASE3.parent
GT = PHASE3 / "data" / "evaluation" / "ground_truth_template.csv"
CAND = PHASE3 / "data" / "evaluation" / "heldout_box_candidates.json"
OUT = Path(__file__).resolve().parent / "results.json"
MODEL = "qwen2.5vl:3b"
URL = "http://127.0.0.1:11434/api/generate"

PROMPTS = {
    "payee_name": "Read the handwritten name in this image exactly as written. Output only the name, nothing else.",
    "amount_words": "Read the handwritten amount in words exactly as written. Output only the words, nothing else.",
    "amount": "Read the handwritten amount in figures exactly as written, including commas and symbols. Output only the figures, nothing else.",
}
EXPECTED_COL = {"payee_name": "payee_name", "amount_words": "amount_words", "amount": "amount_figures"}


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(p, g):
    return lev(p, g) / max(1, len(g))


def wer(p, g):
    pw, gw = p.split(), g.split()
    return lev(pw, gw) / max(1, len(gw))


def ask(crop_gray, prompt):
    small = cv2.resize(crop_gray, (max(1, crop_gray.shape[1] // 2), max(1, crop_gray.shape[0] // 2)))
    ok, buf = cv2.imencode(".png", small)
    payload = {"model": MODEL, "prompt": prompt, "images": [base64.b64encode(buf).decode()], "stream": False,
               "options": {"temperature": 0}}
    r = requests.post(URL, json=payload, timeout=900)
    return r.json().get("response", "").strip()


def invalid(field, text):
    if field == "amount":
        return bool(re.search(r"[A-Za-z]", text))
    return bool(re.search(r"\d", text))


def main():
    gt = [r for r in csv.DictReader(open(GT, encoding="utf-8", newline="")) if r["role"] == "held-out" and r["date"]]
    cand = json.loads(CAND.read_text(encoding="utf-8"))
    report = {"model": MODEL, "held_out_cheques": len(gt), "fields": {}}
    for field in ["amount", "amount_words", "payee_name"]:
        rows = []
        for r in gt:
            cid = r["cheque_id"]
            img = cv2.imread(str(PROJECT / r["image_path"]), cv2.IMREAD_GRAYSCALE)
            x, y, w, h = cand[cid]["fields"][field]["box"]
            H, W = img.shape[:2]
            crop = img[max(0, int(y * H) - 3):int((y + h) * H) + 3, max(0, int(x * W) - 3):int((x + w) * W) + 3]
            raw = ask(crop, PROMPTS[field])
            exp = r[EXPECTED_COL[field]].strip()
            pred = raw.strip().strip('"').strip()
            rows.append({"cheque_id": cid, "expected": exp, "raw": raw, "exact": pred == exp,
                         "cer": round(cer(pred, exp), 3), "wer": round(wer(pred, exp), 3),
                         "invalid": invalid(field, pred)})
            print(field, cid, "->", pred, flush=True)
        report["fields"][field] = {
            "exact": f"{sum(x['exact'] for x in rows)}/{len(rows)}",
            "mean_cer": round(sum(x["cer"] for x in rows) / len(rows), 3),
            "mean_wer": round(sum(x["wer"] for x in rows) / len(rows), 3),
            "invalid_outputs": sum(1 for x in rows if x["invalid"]),
            "rows": rows,
        }
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
