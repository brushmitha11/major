from pathlib import Path
import ast
import re

path = Path("utils/field_extraction_pipeline.py")

if not path.exists():
    raise SystemExit(f"ERROR: File not found: {path.resolve()}")

source = path.read_text(encoding="utf-8")
ast.parse(source)
print("PASS: Python syntax is valid")
print(f"File size: {path.stat().st_size} bytes")

tree = ast.parse(source)
target_methods = {
    "extract_micr_code",
    "extract_cheque_number",
    "extract_amount_figures",
    "extract_account_number",
    "extract_all_fields",
}

for node in ast.walk(tree):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        if node.name in target_methods:
            print(f"\n{'=' * 65}")
            print(f"METHOD: {node.name}, lines {node.lineno}-{node.end_lineno}")
            print("=" * 65)
            print("\n".join(source.splitlines()[node.lineno - 1:node.end_lineno]))

print("\nREGEX SANITY CHECK")
samples = [
    (r"\bMICR\b", "309062500211012:42616031"),
    (r"(?<!\d)(\d{6})(\d{9}):(\d{6,})(?!\d)",
     "309062500211012:42616031"),
    (r"(?<![\d/])((?:\d{1,3}(?:,\d{2,3})+|\d{2,})(?:\.\d{1,2})?)\s*/-(?!\d)",
     "329,000/-"),
]

for pattern, sample in samples:
    match = re.search(pattern, sample, re.IGNORECASE)
    print(f"Pattern: {pattern}")
    print(f"Input:   {sample}")
    print(f"Match:   {match.group(0) if match else None}")
    if match:
        print(f"Groups:  {match.groups()}")
    print("-" * 40)
