import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = {
    "TrOCR improved": ROOT / "experiments/trocr_improved/results.json",
    "Qwen 3b zero-shot": ROOT / "experiments/vision_qwen/results.json",
    "Qwen 7b zero-shot": ROOT / "experiments/vision_qwen/results_7b.json",
    "Qwen 7b few-shot": ROOT / "experiments/vision_qwen/results_7b_fewshot.json",
}

print(f"{'model':20}{'field':15}{'exact':8}{'CER':8}{'WER':8}")
for name, path in FILES.items():
    data = json.loads(path.read_text(encoding="utf-8"))
    for field, d in data["fields"].items():
        print(f"{name:20}{field:15}{d['exact']:8}{d['mean_cer']:<8}{d['mean_wer']:<8}")
