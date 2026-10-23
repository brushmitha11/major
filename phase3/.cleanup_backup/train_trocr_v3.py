"""
TrOCR v3: encoder and decoder fine-tuned on confirmed training cheques (amount, amount in words,
payee name), with an internal validation split of training cheques for model selection,
light augmentation, and constrained decoding. The five held-out cheques are only used for the final score.
"""
import json
import random
import sys
from pathlib import Path

import cv2
import numpy as np
import torch
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_handwritten_v2 as v2
import train_trocr_cheque as T

PHASE3 = T.PHASE3
PROJECT = T.PROJECT
MODEL_OUT = PHASE3 / "models" / "trocr_cheque_v3"
RESULTS = PHASE3 / "data" / "evaluation" / "finetune_v3_results.json"
EPOCHS = 8
LR = 1e-5
BATCH = 4
VAL_FRACTION = 0.2
SEED = 2026


def load_text_samples(rows, meta):
    samples = []
    for r in rows:
        if r["unreadable"] == "yes" or not r["value"] or r["field"] not in T.TEXT_TRAIN_FIELDS:
            continue
        uid, field, value = r["cheque_id"], r["field"], r["value"]
        img = cv2.imread(str(PROJECT / ("datasets/raw/idrbt/300/Cheque " + uid.split("_")[0] + ".tif")),
                         cv2.IMREAD_GRAYSCALE)
        crop = v2.crop_box(img, meta[uid]["fields"][field]["box"])
        samples.append({"cid": uid, "field": field, "crop": crop, "text": value})
    return samples


def augment(gray, rng):
    h, w = gray.shape[:2]
    angle = rng.uniform(-2.0, 2.0)
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    out = cv2.warpAffine(gray, m, (w, h), borderValue=255)
    alpha = rng.uniform(0.85, 1.15)
    beta = rng.uniform(-15, 15)
    return np.clip(out.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)


def split_cheques(samples):
    cids = sorted({s["cid"] for s in samples})
    rng = random.Random(SEED)
    rng.shuffle(cids)
    n_val = max(1, int(round(len(cids) * VAL_FRACTION)))
    val = set(cids[:n_val])
    train = [s for s in samples if s["cid"] not in val]
    valid = [s for s in samples if s["cid"] in val]
    return train, valid, sorted(val)


def val_loss(model, proc, valid):
    model.eval()
    losses = []
    with torch.no_grad():
        for s in range(0, len(valid), BATCH):
            chunk = valid[s:s + BATCH]
            pix = proc(images=[v2.pad_to_square(x["crop"]) for x in chunk], return_tensors="pt").pixel_values
            labels = proc.tokenizer([x["text"] for x in chunk], padding=True, return_tensors="pt").input_ids
            labels[labels == proc.tokenizer.pad_token_id] = -100
            losses.append(float(model(pixel_values=pix, labels=labels).loss))
    model.train()
    return float(np.mean(losses))


def main():
    rng = random.Random(SEED)
    np_rng = np.random.RandomState(SEED)
    meta = json.loads(T.META.read_text(encoding="utf-8"))
    rows = T.load_training_rows()
    samples = load_text_samples(rows, meta)
    train_s, valid_s, val_cheques = split_cheques(samples)
    print("text samples:", len(samples), "train:", len(train_s), "internal validation:", len(valid_s),
          "validation cheques:", val_cheques, flush=True)

    gt_rows = list(__import__("csv").DictReader(open(T.GT, encoding="utf-8", newline="")))
    cand = json.loads(T.CAND.read_text(encoding="utf-8"))
    items = T.build_eval_items(gt_rows, cand)

    proc = TrOCRProcessor.from_pretrained("microsoft/trocr-base-handwritten")
    digit_ids, letter_ids = T.build_bans(proc.tokenizer)
    T.BANNED.update({"amount": letter_ids, "amount_words": digit_ids, "payee_name": digit_ids})

    base = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten").eval()
    base_per = T.evaluate(proc, base, items)
    print("baseline:", T.summarise(base_per), flush=True)
    del base

    model = VisionEncoderDecoderModel.from_pretrained("microsoft/trocr-base-handwritten")
    tok = proc.tokenizer
    for cfg in [model.config, model.config.decoder]:
        cfg.pad_token_id = tok.pad_token_id
        cfg.bos_token_id = tok.cls_token_id
        cfg.eos_token_id = tok.sep_token_id
    model.config.decoder_start_token_id = tok.cls_token_id
    model.train()
    opt = torch.optim.AdamW(model.parameters(), lr=LR)

    best = (float("inf"), None, 0)
    for epoch in range(1, EPOCHS + 1):
        order = np_rng.permutation(len(train_s))
        losses = []
        for s in range(0, len(order), BATCH):
            chunk = [train_s[i] for i in order[s:s + BATCH]]
            imgs = [v2.pad_to_square(augment(x["crop"], rng)) for x in chunk]
            pix = proc(images=imgs, return_tensors="pt").pixel_values
            labels = tok([x["text"] for x in chunk], padding=True, return_tensors="pt").input_ids
            labels[labels == tok.pad_token_id] = -100
            loss = model(pixel_values=pix, labels=labels).loss
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            losses.append(float(loss))
        vl = val_loss(model, proc, valid_s)
        print(f"epoch {epoch} train loss {np.mean(losses):.3f} internal validation loss {vl:.3f}", flush=True)
        if vl < best[0]:
            best = (vl, {k: v.detach().clone() for k, v in model.state_dict().items()}, epoch)

    model.load_state_dict(best[1])
    print(f"best epoch {best[2]} (internal validation loss {best[0]:.3f})", flush=True)
    model.eval()
    MODEL_OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(MODEL_OUT)
    proc.save_pretrained(MODEL_OUT)

    ft_per = T.evaluate(proc, model, items)
    print("fine-tuned (held-out):", T.summarise(ft_per), flush=True)
    leaks = {
        "digits_in_amount_words": sum(1 for r in ft_per if any(c.isdigit() for c in r["amount_words"]["predicted"])),
        "digits_in_payee_name": sum(1 for r in ft_per if any(c.isdigit() for c in r["payee_name"]["predicted"])),
        "letters_in_amount": sum(1 for r in ft_per if any(c.isalpha() for c in r["amount"]["predicted"])),
    }
    print("constraint violations:", leaks, flush=True)

    RESULTS.write_text(json.dumps({
        "text_samples": len(samples),
        "internal_validation_cheques": val_cheques,
        "best_epoch": best[2],
        "baseline_summary": T.summarise(base_per),
        "finetuned_summary": T.summarise(ft_per),
        "constraint_violations": leaks,
        "baseline": base_per,
        "finetuned": ft_per,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("wrote", RESULTS, flush=True)


if __name__ == "__main__":
    main()
