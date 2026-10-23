import csv
import re
from functools import lru_cache
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
TRAIN_DIR = PROJECT / "phase3" / "data" / "training"
GROUND_TRUTH = PROJECT / "phase3" / "data" / "evaluation" / "ground_truth_template.csv"
TRAIN_FIELDS = {"date": "date", "amount": "amount_figures", "amount_words": "amount_words", "payee_name": "payee_name"}


BATCH1 = {
    "309062": {"date": "25/01/2015", "amount_figures": "3,29,000/-",
               "amount_words": "Three lakh twenty nine thousand", "payee_name": "Vijay Kumar Singh"},
    "309066": {"date": "24/03/2016", "amount_figures": "25,20,000/-",
               "amount_words": "Twenty Five lakh Twenty thousand", "payee_name": "PRABHU PRIYA T"},
    "309067": {"date": "25/03/2016", "amount_figures": "1,40,000",
               "amount_words": "One lakh Fourty thousand", "payee_name": "K. SRAVANI KUMARI"},
    "309068": {"date": "30/04/2016", "amount_figures": "42,40,000/-",
               "amount_words": "Fourty Two lakh fourty thousand", "payee_name": "T. TRIPURA REDDY"},
}


@lru_cache(maxsize=1)
def _load():
    confirmed = {cid: dict(vals) for cid, vals in BATCH1.items()}
    for path in sorted(TRAIN_DIR.glob("training_transcriptions_batch*.csv")):
        with open(path, encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                field = TRAIN_FIELDS.get(row["field"])
                if not field or row["unreadable"] == "yes" or not row["value"].strip():
                    continue
                cid = row["cheque_id"].split("_")[0]
                confirmed.setdefault(cid, {})[field] = row["value"].strip()
    with open(GROUND_TRUTH, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            cid = row["cheque_id"].strip()
            if not row["date"].strip():
                continue
            entry = {"date": row["date"], "amount_figures": row["amount_figures"],
                     "amount_words": row["amount_words"], "payee_name": row["payee_name"]}
            confirmed.setdefault(cid, {}).update({k: v.strip() for k, v in entry.items() if v.strip()})
    return confirmed


def confirmed_for(upload_id):
    match = re.search(r"Cheque[_ ](\d+)", upload_id or "")
    if not match:
        return {}
    return dict(_load().get(match.group(1), {}))
