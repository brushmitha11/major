import base64
import difflib
import json
import os
import re
import tempfile
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from date_cells import find_date_strip
import uuid

import cv2
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL = os.environ.get("VLM_MODEL", "qwen2.5vl:3b")
MAX_WIDTH = int(os.environ.get("VLM_MAX_WIDTH", "1000"))
WORDS = [
    "Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "Eleven",
    "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty",
    "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety", "Hundred", "Thousand", "Lakh",
    "Crore", "Rupees", "Paise", "Only",
]
PROMPT = (
    "This is an Indian bank cheque. Read the handwritten fields and return only a JSON object with these keys: "
    "\"date\" (the date is written in eight boxes labelled D D M M Y Y Y Y: read each box left to right as one digit "
    "and return DD/MM/YYYY), \"account_number\" (the printed digits in the A/C No. box, digits only), "
    "\"cheque_number\" (the first 6 digits of the printed MICR line at the bottom), "
    "\"micr_code\" (the 9 digits after the cheque number on the MICR line), "
    "\"amount_figures\" (the amount in the box marked with the rupee sign: read every digit "
    "from left to right and format with Indian commas and /-, for example 1,20,000/-), \"amount_words\" (read the words "
    "one by one from left to right), \"payee_name\" (read the name word by word, keeping initials and capitals), "
    "For amount_words, use only these words: " + ", ".join(WORDS) + ". "
    "Use ? for any character you cannot read. Do not add any other text."
)
_WORD_LOOKUP = {w.lower(): w for w in WORDS}
_WORD_ALIASES = {"lacs": "Lakh", "lacks": "Lakh", "lakhs": "Lakh", "lac": "Lakh", "crores": "Crore"}


@app.post("/extract/handwriting")
def extract_handwriting():
    upload = request.files.get("image")
    if upload is None:
        return jsonify(status="ERROR", error="no image uploaded"), 400
    raw = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.tif")
    upload.save(raw)
    img = cv2.imread(raw, cv2.IMREAD_GRAYSCALE)
    os.remove(raw)
    if img is None:
        return jsonify(status="ERROR", error="could not read image"), 400
    if img.shape[1] > MAX_WIDTH:
        scale = MAX_WIDTH / img.shape[1]
        img = cv2.resize(img, (MAX_WIDTH, int(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".png", img)
    payload = {
        "model": MODEL,
        "prompt": PROMPT,
        "images": [base64.b64encode(buf).decode()],
        "stream": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": 200, "num_ctx": 2048},
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=1500)
        reply = r.json().get("response", "")
        print(f"DEBUG: Ollama raw response: {reply[:200]}")  # Log first 200 chars
    except requests.RequestException as e:
        print(f"DEBUG: Ollama connection error: {e}")
        return jsonify(status="ERROR", error=str(e)), 502
    try:
        fields = json.loads(reply)
        print(f"DEBUG: Parsed fields: {fields}")  # Log parsed result
    except json.JSONDecodeError as e:
        print(f"DEBUG: JSON parse error: {e}, raw: {reply[:300]}")
        return jsonify(status="PARSE_ERROR", error="model did not return JSON", raw=reply), 200
    strip = find_date_strip(img)
    if strip is not None:
        digits = read_date_strip(strip)
        if digits:
            fields["date"] = digits
    fields = format_fields(fields)
    return jsonify(status="OK", fields=fields, raw=reply, model=MODEL)


def read_date_strip(strip):
    big = cv2.resize(strip, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    ok, buf = cv2.imencode(".png", big)
    payload = {
        "model": MODEL,
        "prompt": "This image shows 8 handwritten digits, one per box, from left to right. Return only a JSON object "
                  "with the key \"digits\" holding those 8 digits as a string.",
        "images": [base64.b64encode(buf).decode()],
        "stream": False,
        "format": "json",
        "keep_alive": "30m",
        "options": {"temperature": 0, "num_predict": 60, "num_ctx": 2048},
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=600)
        digits = json.loads(r.json().get("response", "{}")).get("digits", "")
    except (requests.RequestException, json.JSONDecodeError, AttributeError):
        return None
    digits = re.sub(r"\D", "", str(digits))
    if len(digits) != 8:
        return None
    return f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"


def indian_commas(digits):
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail]) if head or groups else tail


def _valid_date(text):
    day, month, year = (int(p) for p in text.split("/"))
    return 1 <= day <= 31 and 1 <= month <= 12 and 2000 <= year <= 2030


def normalise_word(token):
    core = re.sub(r"[^A-Za-z?]", "", token)
    if not core or "?" in core:
        return token
    exact = _WORD_LOOKUP.get(core.lower()) or _WORD_ALIASES.get(core.lower())
    if exact:
        return exact
    close = difflib.get_close_matches(core.lower(), list(_WORD_LOOKUP), n=1, cutoff=0.6)
    return _WORD_LOOKUP[close[0]] if close else token


_UNITS = {w.lower(): i for i, w in enumerate(WORDS[:20])}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_SCALES = {"thousand": 1000, "lakh": 100000, "crore": 10000000}


def words_to_number(text):
    total, current, seen = 0, 0, False
    for token in text.lower().split():
        token = re.sub(r"[^a-z]", "", token)
        if token in _UNITS:
            current += _UNITS[token]
        elif token in _TENS:
            current += _TENS[token]
        elif token == "hundred":
            current = (current or 1) * 100
        elif token in _SCALES:
            total += (current or 1) * _SCALES[token]
            current = 0
        else:
            continue
        seen = True
    return total + current if seen else None


def format_fields(fields):
    date = fields.get("date")
    if isinstance(date, str):
        digits = re.sub(r"\D", "", date)
        if len(digits) == 8:
            candidate = f"{digits[:2]}/{digits[2:4]}/{digits[4:]}"
        elif len(digits) == 6:
            candidate = f"{digits[:2]}/{digits[2:4]}/20{digits[4:]}"
        else:
            candidate = None
        if candidate and _valid_date(candidate):
            fields["date"] = candidate
        else:
            fields["date"] = None
    words = fields.get("amount_words")
    if isinstance(words, str):
        fields["amount_words"] = " ".join(normalise_word(w) for w in words.split())
    amount = fields.get("amount_figures")
    if isinstance(amount, str):
        digits = re.sub(r"\D", "", amount)
        if digits:
            fields["amount_figures"] = f"{indian_commas(digits.lstrip('0') or '0')}/-"
        else:
            from_words = words_to_number(fields.get("amount_words") or "")
            if from_words:
                fields["amount_figures"] = f"{indian_commas(str(from_words))}/-"
    return fields


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8002)
