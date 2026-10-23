"""
Fine-tune TrOCR on confirmed training cheques; evaluate on confirmed held-out cheques.

Training data: confirmed values for training-split cheques only (083657 from the ground-truth
sheet, plus the exported training transcriptions with 309063 removed). Boxes come from the
verified labels in metadata.json.

Evaluation data: the five held-out cheques with confirmed values in ground_truth_template.csv.
Their boxes are candidate boxes (unverified), so the scores depend on those boxes.

Writes:
  phase3/models/trocr_cheque_ft/            (fine-tuned weights; base model is not modified)
  phase3/data/training/training_transcriptions.csv
  phase3/data/evaluation/finetune_results.json
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_handwritten_v2 as v2

PROJECT = Path(__file__).resolve().parent.parent
PHASE3 = PROJECT / "phase3"
META = PHASE3 / "data" / "annotations" / "metadata.json"
GT = PHASE3 / "data" / "evaluation" / "ground_truth_template.csv"
CAND = PHASE3 / "data" / "evaluation" / "heldout_box_candidates.json"
TRAIN_CSV = PHASE3 / "data" / "training" / "training_transcriptions.csv"
MODEL_OUT = PHASE3 / "models" / "trocr_cheque_text"
DATE_MODEL = PHASE3 / "models" / "trocr_cheque_date"
RESULTS = PHASE3 / "data" / "evaluation" / "finetune_text_results.json"

EXPORTED = """"cheque_id","field","value","unreadable"
"309062_reference","date","25/01/2015","no"
"309062_reference","amount","3,29,000/-","no"
"309062_reference","amount_words","Three lakh twenty nine thousand","no"
"309062_reference","payee_name","Vijay Kumar Singh","no"
"309066_reference","date","24/03/2016","no"
"309066_reference","amount","25,20,000/-","no"
"309066_reference","amount_words","Twenty Five lakh Twenty thousand","no"
"309066_reference","payee_name","PRABHU PRIYA T","no"
"309067_reference","date","25/03/2016","no"
"309067_reference","amount","1,40,000","no"
"309067_reference","amount_words","One lakh Fourty thousand","no"
"309067_reference","payee_name","K. SRAVANI KUMARI","no"
"309068_reference","date","30/04/2016","no"
"309068_reference","amount","42,40,000/-","no"
"309068_reference","amount_words","Fourty Two lakh fourty thousand","no"
"309068_reference","payee_name","T. TRIPURA REDDY","no"
"""

FIELDS = ["date", "amount", "amount_words", "payee_name"]
HELD_FIELDS = ["amount", "amount_words", "payee_name"]
TEXT_TRAIN_FIELDS = {"amount", "amount_words", "payee_name"}


def load_training_rows():
    TRAIN_CSV.parent.mkdir(parents=True, exist_ok=True)
    TRAIN_CSV.write_text(EXPORTED, encoding="utf-8")
    rows = list(csv.DictReader(EXPORTED.splitlines()))
    for name in ["training_transcriptions_batch2.csv", "training_transcriptions_batch3.csv", "training_transcriptions_batch4.csv", "training_transcriptions_batch5.csv", "training_transcriptions_batch6.csv", "training_transcriptions_batch7.csv", "training_transcriptions_batch8.csv", "training_transcriptions_batch9.csv", "training_transcriptions_batch10.csv"]:
        extra = PHASE3 / "data" / "training" / name
        if extra.exists():
            rows += list(csv.DictReader(open(extra, encoding="utf-8", newline="")))
    gt = list(csv.DictReader(open(GT, encoding="utf-8", newline="")))
    for r in gt:
        if r["cheque_id"] == "083657":
            for f, col in [("date", "date"), ("amount", "amount_figures"),
                           ("amount_words", "amount_words"), ("payee_name", "payee_name")]:
                rows.append({"cheque_id": "083657_reference", "field": f,
                             "value": r[col], "unreadable": "no"})
    return rows


def digits_of(date_value):
    return "".join(ch for ch in date_value if ch.isdigit())


def build_training_samples(rows, meta):
    samples = []
    for r in rows:
        if r["unreadable"] == "yes" or not r["value"]:
            continue
        uid, field, value = r["cheque_id"], r["field"], r["value"]
        if field not in TEXT_TRAIN_FIELDS:
            continue
        img = cv2.imread(str(PROJECT / ("datasets/raw/idrbt/300/Cheque " + uid.split("_")[0] + ".tif")),
                         cv2.IMREAD_GRAYSCALE)
        box = meta[uid]["fields"][field]["box"]
        crop = v2.crop_box(img, box)
        if field == "date":
            digits = digits_of(value)
            h, w = crop.shape[:2]
            cw = w / 8.0
            for i in range(8):
                a, b = int(i * cw) + 4, int((i + 1) * cw) - 4
                samples.append((crop[:, a:b], digits[i]))
        else:
            samples.append((crop, value))
    return samples


def build_eval_items(gt_rows, cand):
    items = []
    for r in gt_rows:
        if r["role"] != "held-out" or not r["date"]:
            continue
        cid = r["cheque_id"]
        img = cv2.imread(str(PROJECT / r["image_path"]), cv2.IMREAD_GRAYSCALE)
        fields = cand[cid]["fields"]
        expected = {"date": r["date"], "amount": r["amount_figures"],
                    "amount_words": r["amount_words"], "payee_name": r["payee_name"]}
        items.append((cid, img, fields, expected))
    return items


def levenshtein(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def cer(pred, gold):
    return levenshtein(pred, gold) / max(1, len(gold))


BANNED = {}


def build_bans(tok):
    vocab = tok.get_vocab()
    digit = [i for t, i in vocab.items() if any(c.isdigit() for c in t)]
    letter = [i for t, i in vocab.items() if any(c.isalpha() for c in t)]
    return digit, letter


def read_field(proc, model, img, box, field):
    crop = v2.crop_box(img, box)
    if field == "date":
        h, w = crop.shape[:2]
        cw = w / 8.0
        pieces = []
        for i in range(8):
            a, b = int(i * cw) + 4, int((i + 1) * cw) - 4
            pieces.append(v2.pad_to_square(crop[:, a:b]))
        texts, _ = v2.recognise(proc, model, pieces)
        return "".join(ch for t in texts for ch in t if ch.isdigit())
    chunks = v2.chunk_line(crop) if field != "amount" else [crop]
    banned = [[i] for i in BANNED.get(field, [])] or None
    texts, _ = v2.recognise(proc, model, [v2.pad_to_square(c) for c in chunks], bad_words_ids=banned)
    return " ".join(t for t in texts if t)


def evaluate(proc, model, items):
    per = []
    for cid, img, fields, expected in items:
        row = {"cheque_id": cid}
        for f in HELD_FIELDS:
            box = fields[f]["box"]
            pred = read_field(proc, model, img, box, f)
            gold = digits_of(expected[f]) if f == "date" else expected[f]
            pred_cmp = pred if f == "date" else pred.strip()
            row[f] = {"expected": expected[f], "predicted": pred,
                      "exact": pred_cmp == gold, "cer": round(cer(pred_cmp, gold), 3)}
        per.append(row)
    return per


def format_date(digits):
    if len(digits) != 8:
        return None, "not 8 digits"
    dd, mm, yyyy = digits[:2], digits[2:4], digits[4:]
    try:
        datetime.strptime(f"{dd}{mm}{yyyy}", "%d%m%Y")
    except ValueError:
        return f"{dd}/{mm}/{yyyy}", "invalid calendar date"
    return f"{dd}/{mm}/{yyyy}", "valid"


def evaluate_dates(items):
    proc = TrOCRProcessor.from_pretrained(str(MODEL_OUT.parent / "trocr_cheque_date"))
    model = VisionEncoderDecoderModel.from_pretrained(DATE_MODEL).eval()
    out = []
    for cid, img, fields, expected in items:
        pred = read_field(proc, model, img, fields["date"]["box"], "date")
        formatted, status = format_date(pred)
        gold = expected["date"]
        out.append({"cheque_id": cid, "expected": gold, "predicted_digits": pred,
                    "formatted": formatted, "status": status,
                    "exact": formatted == gold})
    return out


def summarise(per):
    out = {}
    for f in HELD_FIELDS:
        exact = sum(1 for r in per if r[f]["exact"])
        cers = [r[f]["cer"] for r in per]
        out[f] = {"exact_match": f"{exact}/{len(per)}", "mean_cer": round(float(np.mean(cers)), 3)}
    return out


def main():
    meta = json.loads(META.read_text(encoding="utf-8"))
    rows = load_training_rows()
    samples = build_training_samples(rows, meta)
    print("training samples:", len(samples), flush=True)

    gt_rows = list(csv.DictReader(open(GT, encoding="utf-8", newline="")))
    cand = json.loads(CAND.read_text(encoding="utf-8"))
    items = build_eval_items(gt_rows, cand)
    print("held-out cheques:", len(items), flush=True)

    proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    digit_ids, letter_ids = build_bans(proc.tokenizer)
    BANNED.update({"amount": letter_ids, "amount_words": digit_ids, "payee_name": digit_ids})
    base = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten").eval()
    base_per = evaluate(proc, base, items)
    print("baseline:", summarise(base_per), flush=True)

    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    tok = proc.tokenizer
    for cfg in [model.config, model.config.decoder]:
        cfg.pad_token_id = tok.pad_token_id
        cfg.bos_token_id = tok.cls_token_id
        cfg.eos_token_id = tok.sep_token_id
    model.config.decoder_start_token_id = tok.cls_token_id
    for p in model.encoder.parameters():
        p.requires_grad = False
    model.train()
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=5e-6)
    batch = 4
    for epoch in range(3):
        order = np.random.RandomState(epoch).permutation(len(samples))
        losses = []
        for s in range(0, len(order), batch):
            idx = order[s:s + batch]
            imgs = [v2.pad_to_square(samples[i][0]) for i in idx]
            texts = [samples[i][1] for i in idx]
            pix = proc(images=imgs, return_tensors="pt").pixel_values
            labels = proc.tokenizer(texts, padding=True, return_tensors="pt").input_ids
            labels[labels == proc.tokenizer.pad_token_id] = -100
            loss = model(pixel_values=pix, labels=labels).loss
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(float(loss))
        print(f"epoch {epoch + 1} mean loss {np.mean(losses):.3f}", flush=True)

    model.eval()
    MODEL_OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(MODEL_OUT)
    proc.save_pretrained(MODEL_OUT)
    ft_per = evaluate(proc, model, items)
    print("fine-tuned:", summarise(ft_per), flush=True)
    leaks = {
        "digits_in_amount_words": sum(1 for r in ft_per if any(c.isdigit() for c in r["amount_words"]["predicted"])),
        "digits_in_payee_name": sum(1 for r in ft_per if any(c.isdigit() for c in r["payee_name"]["predicted"])),
        "letters_in_amount": sum(1 for r in ft_per if any(c.isalpha() for c in r["amount"]["predicted"])),
    }
    print("constraint violations:", leaks, flush=True)

    date_per = evaluate_dates(items)
    print("date (dd/mm/yyyy):", sum(1 for r in date_per if r["exact"]), "of", len(date_per), flush=True)

    RESULTS.write_text(json.dumps({
        "training_samples": len(samples),
        "held_out_cheques": len(items),
        "baseline_summary": summarise(base_per),
        "finetuned_summary": summarise(ft_per),
        "date_results": date_per,
        "constraint_violations": leaks,
        "baseline": base_per,
        "finetuned": ft_per,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", RESULTS, flush=True)


if __name__ == "__main__":
    main()
