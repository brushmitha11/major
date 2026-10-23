"""
Evaluate qwen2.5vl:7b with few-shot learning (in-context examples from training set).

Inputs: confirmed held-out values (ground_truth_template.csv), candidate boxes (unverified),
        and training examples for few-shot prompting.
Outputs: experiments/vision_qwen/results_7b_fewshot.json with exact match, CER, WER.
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
OUT = Path(__file__).resolve().parent / "results_7b_fewshot.json"
MODEL = "qwen2.5vl:7b"
URL = "http://127.0.0.1:11434/api/generate"

# Training examples for few-shot prompting
TRAINING_EXAMPLES = {
    "payee_name": [
        "Neelam Anirudh Kumar",
        "Ramini Avinash Yadav",
        "Kanji Prem Chand Kumar",
    ],
    "amount_words": [
        "Six lacks Twenty thousand",
        "Three lacks Thirty thousand",
        "One lakh Twenty five thousand",
    ],
    "amount": [
        "6,20,000/-",
        "3,30,000/-",
        "1,25,000/-",
    ],
}

PROMPTS = {
    "payee_name": f"""Read the handwritten name in this image exactly as written. Output only the name, nothing else.

Examples from similar cheques:
- {TRAINING_EXAMPLES['payee_name'][0]}
- {TRAINING_EXAMPLES['payee_name'][1]}
- {TRAINING_EXAMPLES['payee_name'][2]}""",

    "amount_words": f"""Read the handwritten amount in words exactly as written. Output only the words, nothing else.

Examples from similar cheques:
- {TRAINING_EXAMPLES['amount_words'][0]}
- {TRAINING_EXAMPLES['amount_words'][1]}
- {TRAINING_EXAMPLES['amount_words'][2]}""",

    "amount": f"""Read the handwritten amount in figures exactly as written, including commas and symbols. Output only the figures, nothing else.

Examples from similar cheques:
- {TRAINING_EXAMPLES['amount'][0]}
- {TRAINING_EXAMPLES['amount'][1]}
- {TRAINING_EXAMPLES['amount'][2]}""",
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
    report = {"model": MODEL, "approach": "few-shot (in-context examples)", "held_out_cheques": len(gt), "fields": {}}

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
