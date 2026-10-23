"""
Few-shot qwen2.5vl:3b on CPU (no training).

Examples come from confirmed training transcriptions (text only), so the model learns the
writing conventions (e.g. "/-", "lakh" spelling). Training cheques use leave-one-out: a
cheque's own label is never in its prompt.

Usage: python evaluate_3b_fewshot.py {heldout|train}
Outputs: results_3b_fewshot_{mode}.json (written after every cheque).
"""
import base64
import csv
import json
import os
import random
import re
import sys
from pathlib import Path

import cv2
import requests

sys.stdout.reconfigure(encoding="utf-8")

PHASE3 = Path(__file__).resolve().parents[2]
PROJECT = PHASE3.parent
TRAIN_DIR = PHASE3 / "data" / "training"
META = PHASE3 / "data" / "annotations" / "metadata.json"
GT = PHASE3 / "data" / "evaluation" / "ground_truth_template.csv"
CAND = PHASE3 / "data" / "evaluation" / "heldout_box_candidates.json"
OUT_DIR = Path(__file__).resolve().parent
MODEL = os.environ.get("VISION_MODEL", "qwen2.5vl:3b")
TAG = os.environ.get("VISION_TAG", "3b")
URL = "http://127.0.0.1:11434/api/generate"
K = 6
SEED = 2026
FIELDS = ["amount", "amount_words", "payee_name"]
GT_COL = {"amount": "amount_figures", "amount_words": "amount_words", "payee_name": "payee_name"}
INSTR = {
    "amount": "Read the handwritten amount in figures exactly as written, including commas, slashes and any '/-' suffix. Output only the figures.",
    "amount_words": "Read the handwritten amount in words exactly as written, keeping the spelling used on the cheque. Output only the words.",
    "payee_name": "Read the handwritten payee name exactly as written. Output only the name.",
}


if os.environ.get("PROMPT_VERSION") == "v2":
    INSTR["amount"] = ("This is the amount in figures on an Indian cheque. Write it exactly as printed, with Indian "
                       "commas (for example 1,20,000) and the \"/-\" suffix if it is there. Read every digit. Output "
                       "only the figures on one line. If a digit is unclear, write ?.")
    INSTR["amount_words"] = ("This is the amount in words on an Indian cheque. Write it exactly as written, keeping the "
                             "spelling on the cheque (for example \"lacks\" or \"fourty\"). Output only the words on one "
                             "line, with no digits. If a word is unclear, write ?.")
    INSTR["payee_name"] = ("This is the payee name on an Indian cheque, handwritten. Write it exactly as written, keeping "
                           "initials and capitals. Output only the name on one line. If a letter is unclear, write ?.")
    FIELDS = os.environ.get("PROMPT_FIELDS", "amount").split(",")

if os.environ.get("PROMPT_VERSION") == "v3":
    VOCAB = ("Zero, One, Two, Three, Four, Five, Six, Seven, Eight, Nine, Ten, Eleven, Twelve, Thirteen, Fourteen, "
             "Fifteen, Sixteen, Seventeen, Eighteen, Nineteen, Twenty, Thirty, Forty, Fifty, Sixty, Seventy, Eighty, "
             "Ninety, Hundred, Thousand, Lakh, Crore, Rupees, Paise, Only")
    INSTR["amount_words"] = ("This is the amount in words on an Indian cheque. Write it exactly as written. Use only "
                             f"these words: {VOCAB}. Output only the words on one line, with no digits. If a word is "
                             "unclear, write ?.")
    FIELDS = ["amount_words"]


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def normalise(s):
    s = s.lower().replace("/-", "")
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return " ".join(s.split())


def crop(img, box, pad=3):
    h, w = img.shape[:2]
    x, y, bw, bh = box
    return img[max(0, int(y * h) - pad):min(h, int((y + bh) * h) + pad),
               max(0, int(x * w) - pad):min(w, int((x + bw) * w) + pad)]


def load_training():
    rows = []
    for path in sorted(TRAIN_DIR.glob("training_transcriptions_batch*.csv")):
        with open(path, encoding="utf-8", newline="") as f:
            rows += list(csv.DictReader(f))
    return [r for r in rows if r["unreadable"] == "no" and r["value"].strip() and r["field"] in FIELDS]


def examples_for(field, exclude_cid, pool):
    cands = [r["value"].strip() for r in pool if r["field"] == field and r["cheque_id"] != exclude_cid]
    rng = random.Random(f"{SEED}-{field}-{exclude_cid}")
    return rng.sample(cands, min(K, len(cands)))


def build_prompt(field, examples):
    shown = "\n".join(f"- {e}" for e in examples)
    return (f"{INSTR[field]}\n\nHow other cheques from this bank write this field "
            f"(text only, for format reference, the image is what you must read):\n{shown}")


def ask(gray, prompt):
    ok, buf = cv2.imencode(".png", gray)
    payload = {"model": MODEL, "prompt": prompt, "images": [base64.b64encode(buf).decode()],
               "stream": False, "keep_alive": "30m",
               "options": {"temperature": 0, "num_predict": 40, "num_ctx": 2048}}
    r = requests.post(URL, json=payload, timeout=240)
    return r.json().get("response", "").strip()


def score(raw, exp):
    pred = raw.strip().strip('"').strip()
    return {
        "exact": pred == exp,
        "exact_norm": normalise(pred) == normalise(exp),
        "cer_norm": round(lev(normalise(pred), normalise(exp)) / max(1, len(normalise(exp))), 3),
    }


def run_heldout(pool, meta):
    cand = json.loads(CAND.read_text(encoding="utf-8"))
    gt = [r for r in csv.DictReader(open(GT, encoding="utf-8", newline=""))
          if r["role"] == "held-out" and r["date"]]
    jobs = []
    for r in gt:
        img = cv2.imread(str(PROJECT / r["image_path"]), cv2.IMREAD_GRAYSCALE)
        for f in FIELDS:
            jobs.append((r["cheque_id"], f, img, cand[r["cheque_id"]]["fields"][f]["box"],
                         r[GT_COL[f]].strip(), None))
    return jobs


def run_train(pool, meta, start, end):
    jobs = []
    for cid in sorted({r["cheque_id"] for r in pool})[start:end]:
        img = cv2.imread(str(PROJECT / ("datasets/raw/idrbt/300/Cheque " + cid.split("_")[0] + ".tif")),
                         cv2.IMREAD_GRAYSCALE)
        expected = {r["field"]: r["value"].strip() for r in pool if r["cheque_id"] == cid}
        for f in FIELDS:
            if f in expected:
                jobs.append((cid, f, img, meta[cid]["fields"][f]["box"], expected[f], cid))
    return jobs


def main(mode, start=0, end=None):
    pool = load_training()
    meta = json.loads(META.read_text(encoding="utf-8"))
    jobs = run_heldout(pool, meta) if mode == "heldout" else run_train(pool, meta, start, end)
    suffix = "" if mode == "heldout" else f"_{start:02d}_{end if end is not None else 'end'}"
    out_path = OUT_DIR / f"results_{TAG}_fewshot_{mode}{suffix}.json"
    report = {"model": MODEL, "approach": f"few-shot K={K}, leave-one-out" if mode == "train"
              else f"few-shot K={K}", "fields": {f: {"rows": []} for f in FIELDS}}
    if out_path.exists():
        previous = json.loads(out_path.read_text(encoding="utf-8"))
        for f in FIELDS:
            report["fields"][f]["rows"] = previous["fields"][f]["rows"]
    done = {(f, r["cheque_id"]) for f in FIELDS for r in report["fields"][f]["rows"]}
    for cid, field, img, box, exp, exclude in jobs:
        if (field, cid) in done:
            continue
        examples = examples_for(field, exclude or "", pool)
        raw = ask(crop(img, box), build_prompt(field, examples))
        s = score(raw, exp)
        report["fields"][field]["rows"].append({"cheque_id": cid, "expected": exp, "raw": raw, **s})
        print(mode, field, cid, "->", raw, "| expected:", exp, flush=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for f in FIELDS:
        rows = report["fields"][f]["rows"]
        n = max(1, len(rows))
        report["fields"][f].update({
            "exact": f"{sum(r['exact'] for r in rows)}/{len(rows)}",
            "exact_norm": f"{sum(r['exact_norm'] for r in rows)}/{len(rows)}",
            "mean_cer_norm": round(sum(r["cer_norm"] for r in rows) / n, 3),
        })
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", out_path, flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args[0], int(args[1]) if len(args) > 1 else 0, int(args[2]) if len(args) > 2 else None)
