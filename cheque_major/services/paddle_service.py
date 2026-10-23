import os
import tempfile
import uuid

import cv2
from flask import Flask, jsonify, request
from paddleocr import PaddleOCR

app = Flask(__name__)
ocr = PaddleOCR(lang="en", use_doc_orientation_classify=False, use_doc_unwarping=False,
                use_textline_orientation=False, enable_mkldnn=False)


@app.post("/extract/text")
def extract_text():
    upload = request.files.get("image")
    if upload is None:
        return jsonify(status="ERROR", error="no image uploaded"), 400

    raw = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.tif")
    upload.save(raw)
    img = cv2.imread(raw)
    os.remove(raw)

    if img is None:
        return jsonify(status="ERROR", error="could not read image"), 400

    # Aggressive optimization: Resize to 1000px width for speed
    max_width = 1000
    if img.shape[1] > max_width:
        scale = max_width / img.shape[1]
        img = cv2.resize(img, (max_width, int(img.shape[0] * scale)), interpolation=cv2.INTER_AREA)

    # Convert to grayscale for faster processing
    if len(img.shape) == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    png = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.png")
    cv2.imwrite(png, img)

    try:
        print(f"[PaddleOCR] Starting extraction on {img.shape}")
        results = ocr.predict(png)
        print(f"[PaddleOCR] Completed with {len(results)} blocks")
    except Exception as e:
        print(f"[PaddleOCR] Error: {e}")
        if os.path.exists(png):
            os.remove(png)
        return jsonify(status="ERROR", error=str(e)), 500
    finally:
        if os.path.exists(png):
            os.remove(png)

    lines = []
    for r in results:
        for text, score in zip(r.get("rec_texts", []), r.get("rec_scores", [])):
            lines.append({"text": text, "confidence": round(float(score), 3)})

    confidence = round(sum(l["confidence"] for l in lines) / len(lines), 3) if lines else None
    return jsonify(status="OK", text=" ".join(l["text"] for l in lines), confidence=confidence, lines=lines)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8001)
