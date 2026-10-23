import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUNS = [
    ("Zero-shot", HERE / "results_7b.json"),
    ("Qwen 7B few-shot", HERE / "results_7b_fewshot.json"),
    ("Qwen 3B few-shot (held-out)", HERE / "results_3b_fewshot_heldout.json"),
]
OUT = HERE / "extracted_7b_report.html"
FIELDS = [("amount", "Amount (figures)"), ("amount_words", "Amount (words)"), ("payee_name", "Payee name")]


def section(title, data):
    blocks = []
    for key, label in FIELDS:
        rows = "".join(
            f"<tr><td>{html.escape(r['cheque_id'])}</td>"
            f"<td>{html.escape(r['expected'])}</td>"
            f"<td class=\"{'ok' if r['exact'] else 'bad'}\">{html.escape(r['raw'])}</td>"
            f"<td>{'match' if r['exact'] else 'differs'}</td></tr>"
            for r in data["fields"][key]["rows"]
        )
        blocks.append(
            f"<h3>{label}</h3><table><tr><th>Cheque</th><th>Ground truth</th>"
            f"<th>Qwen 7B output</th><th></th></tr>{rows}</table>"
        )
    return f"<section><h2>{html.escape(title)}</h2>{''.join(blocks)}</section>"


def main():
    parts = []
    for title, path in RUNS:
        if path.exists():
            parts.append(section(title, json.loads(path.read_text(encoding="utf-8"))))
    page = f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Qwen 7B Extracted Cheque Data</title>
<style>
  :root {{ --bg:#f7f7f5; --fg:#222; --card:#fff; --line:#ddd; --ok:#e7f6ec; --bad:#fbe9e7; }}
  @media (prefers-color-scheme: dark) {{
    :root:not([data-theme="light"]) {{ --bg:#1b1c1e; --fg:#e8e8e8; --card:#26282b; --line:#3a3d41; --ok:#1f3a2a; --bad:#4a2420; }}
  }}
  :root[data-theme="dark"] {{ --bg:#1b1c1e; --fg:#e8e8e8; --card:#26282b; --line:#3a3d41; --ok:#1f3a2a; --bad:#4a2420; }}
  body {{ background:var(--bg); color:var(--fg); font-family:Arial,sans-serif; margin:0; padding:16px; }}
  main {{ max-width:960px; margin:0 auto; }}
  section {{ background:var(--card); border:1px solid var(--line); border-radius:8px; padding:16px; margin-bottom:24px; }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:12px; font-size:15px; }}
  th, td {{ text-align:left; padding:8px; border-bottom:1px solid var(--line); word-break:break-word; }}
  td.ok {{ background:var(--ok); }}
  td.bad {{ background:var(--bad); }}
  p.note {{ font-size:14px; opacity:.8; }}
</style>
<body>
<main>
<h1>Qwen 2.5-VL 7B: extracted cheque data</h1>
<p class="note">Held-out cheques 100828, 100831, 083655, 083654, 083656. Green = output matches the ground truth exactly. Red = differs. Strict string match, so "22,23,000" vs "22,23,000/-" counts as differs.</p>
{''.join(parts)}
</main>
</body>
"""
    OUT.write_text(page, encoding="utf-8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
