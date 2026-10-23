"""
Improved TrOCR experiment (text fields: payee name, amount in words, amount in figures).

Changes vs previous run:
- Amount values for cheques whose figures and words disagree are excluded from training.
- Training is split by cheque; the best epoch is chosen on an internal validation split of training cheques.
- Raw and validated outputs are both saved; validation rules flag digits/letters violations, not corrections.
- Adds word error rate (WER) and invalid-output rate.

The five held-out cheques are used only for the final evaluation.
"""
import json
import random
import re
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

PHASE3 = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PHASE3))
import train_trocr_cheque as T
import extract_handwritten_v2 as v2

EXP = Path(__file__).resolve().parent
CKPT = EXP / "checkpoint"
SEED = 2026
EPOCHS = 4
LR = 5e-6
BATCH = 4
VAL_FRACTION = 0.2
EXCLUDE_AMOUNT = {"309078_reference", "309079_reference", "309102_reference", "309117_reference"}
FIELDS = ["amount", "amount_words", "payee_name"]


def wer(pred, gold):
    p, g = pred.split(), gold.split()
    d = list(range(len(p) + 1))
    for i, gw in enumerate(g, 1):
        prev, d[0] = d[0], i
        for j, pw in enumerate(p, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (gw != pw))
            prev, d[j] = d[j], cur
    return d[len(p)] / max(1, len(g))


def load_samples(rows, meta):
    out = []
    for r in rows:
        if r["unreadable"] == "yes" or not r["value"] or r["field"] not in FIELDS:
            continue
        if r["field"] == "amount" and r["cheque_id"] in EXCLUDE_AMOUNT:
            continue
        uid = r["cheque_id"]
        img = T.cv2.imread(str(T.PROJECT / ("datasets/raw/idrbt/300/Cheque " + uid.split("_")[0] + ".tif")),
                           T.cv2.IMREAD_GRAYSCALE)
        crop = v2.crop_box(img, meta[uid]["fields"][r["field"]]["box"])
        out.append({"cid": uid, "field": r["field"], "crop": crop, "text": r["value"]})
    return out


def main():
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    meta = json.loads(T.META.read_text(encoding="utf-8"))
    rows = T.load_training_rows()
    samples = load_samples(rows, meta)
    cids = sorted({s["cid"] for s in samples})
    rng = random.Random(SEED)
    rng.shuffle(cids)
    val_c = set(cids[:max(1, round(len(cids) * VAL_FRACTION))])
    train_s = [s for s in samples if s["cid"] not in val_c]
    val_s = [s for s in samples if s["cid"] in val_c]
    print("samples:", len(samples), "train:", len(train_s), "internal validation:", len(val_s),
          "validation cheques:", len(val_c), flush=True)

    gt_rows = list(__import__("csv").DictReader(open(T.GT, encoding="utf-8", newline="")))
    cand = json.loads(T.CAND.read_text(encoding="utf-8"))
    items = T.build_eval_items(gt_rows, cand)
    proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    digit_ids, letter_ids = T.build_bans(proc.tokenizer)
    T.BANNED.update({"amount": letter_ids, "amount_words": digit_ids, "payee_name": digit_ids})

    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    tok = proc.tokenizer
    for cfg in [model.config, model.config.decoder]:
        cfg.pad_token_id, cfg.bos_token_id, cfg.eos_token_id = tok.pad_token_id, tok.cls_token_id, tok.sep_token_id
    model.config.decoder_start_token_id = tok.cls_token_id
    for p in model.encoder.parameters():
        p.requires_grad = False
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR)

    def val_loss():
        model.eval()
        ls = []
        with torch.no_grad():
            for s in range(0, len(val_s), BATCH):
                ch = val_s[s:s + BATCH]
                pix = proc(images=[v2.pad_to_square(x["crop"]) for x in ch], return_tensors="pt").pixel_values
                lab = tok([x["text"] for x in ch], padding=True, return_tensors="pt").input_ids
                lab[lab == tok.pad_token_id] = -100
                ls.append(float(model(pixel_values=pix, labels=lab).loss))
        model.train()
        return float(np.mean(ls))

    best = (float("inf"), None, 0)
    model.train()
    for epoch in range(1, EPOCHS + 1):
        order = np.random.permutation(len(train_s))
        losses = []
        for s in range(0, len(order), BATCH):
            ch = [train_s[i] for i in order[s:s + BATCH]]
            pix = proc(images=[v2.pad_to_square(x["crop"]) for x in ch], return_tensors="pt").pixel_values
            lab = tok([x["text"] for x in ch], padding=True, return_tensors="pt").input_ids
            lab[lab == tok.pad_token_id] = -100
            loss = model(pixel_values=pix, labels=lab).loss
            opt.zero_grad()
            loss.backward()
            opt.step()
            losses.append(float(loss))
        vl = val_loss()
        print(f"epoch {epoch} train {np.mean(losses):.3f} internal validation {vl:.3f}", flush=True)
        if vl < best[0]:
            best = (vl, {k: v.detach().clone() for k, v in model.state_dict().items()}, epoch)
    model.load_state_dict(best[1])
    model.eval()
    CKPT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(CKPT)
    proc.save_pretrained(CKPT)
    print("best epoch", best[2], flush=True)

    per = T.evaluate(proc, model, items)
    report = {"config": {"epochs": EPOCHS, "lr": LR, "batch": BATCH, "encoder_frozen": True,
                         "excluded_amount_cheques": sorted(EXCLUDE_AMOUNT), "seed": SEED,
                         "best_epoch": best[2], "samples": len(samples), "train": len(train_s),
                         "internal_validation": len(val_s)},
              "fields": {}}
    for f in FIELDS:
        exact = [r[f]["exact"] for r in per]
        cers = [r[f]["cer"] for r in per]
        wers = [wer(r[f]["predicted"], r[f]["expected"]) for r in per]
        invalid = sum(1 for r in per if (f == "amount" and re.search(r"[A-Za-z]", r[f]["predicted"])) or
                      (f != "amount" and re.search(r"\d", r[f]["predicted"])))
        report["fields"][f] = {"exact": f"{sum(exact)}/{len(per)}", "mean_cer": round(float(np.mean(cers)), 3),
                               "mean_wer": round(float(np.mean(wers)), 3), "invalid_outputs": invalid,
                               "rows": [{"cheque_id": r["cheque_id"], "expected": r[f]["expected"],
                                         "predicted": r[f]["predicted"], "exact": r[f]["exact"]} for r in per]}
        print(f, report["fields"][f]["exact"], "CER", report["fields"][f]["mean_cer"],
              "WER", report["fields"][f]["mean_wer"], "invalid", invalid, flush=True)
    (EXP / "results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", EXP / "results.json", flush=True)


if __name__ == "__main__":
    main()
