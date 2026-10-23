import json
import re
import sys
from pathlib import Path

from amount_words import amount_to_words

ROOT = Path(__file__).resolve().parent


def norm(s):
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s.lower().replace("/-", "")).split())


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


def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    figures = data["fields"]["amount"]["rows"]
    words = data["fields"]["amount_words"]["rows"]
    n = len(words)
    direct_exact = rule_exact = 0
    direct_cer = rule_cer = 0.0
    for fig, w in zip(figures, words):
        gold = norm(w["expected"])
        direct = norm(w["raw"])
        rule = norm(amount_to_words(fig["raw"]))
        direct_exact += direct == gold
        rule_exact += rule == gold
        direct_cer += cer(direct, gold)
        rule_cer += cer(rule, gold)
        print(f"{w['cheque_id']} | model words: {w['raw']} | from figures: {amount_to_words(fig['raw'])} | gold: {w['expected']}")
    print(f"model reads words directly: exact {direct_exact}/{n}, mean CER {direct_cer / n:.3f}")
    print(f"words derived from figures: exact {rule_exact}/{n}, mean CER {rule_cer / n:.3f}")


if __name__ == "__main__":
    main(sys.argv[1])
