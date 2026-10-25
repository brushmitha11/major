"""
Ollama Qwen2.5-VL implementation for cheque handwriting extraction.
Uses the existing local Ollama model; no Transformers or PyTorch required.
"""
import uuid
import base64
import io
import json
import logging
import re
import urllib.request
import urllib.error
from typing import Dict, Any

logger = logging.getLogger(__name__)


class VLMExtractorLocal:
    """Extract handwritten cheque fields using Qwen through Ollama."""

    def __init__(self, config):
        self.config = config
        self.enabled = bool(getattr(config, "ENABLE_QWEN_VLM", False))
        self.model = getattr(config, "OLLAMA_MODEL", "qwen2.5vl:3b")
        self.api_url = getattr(
            config, "OLLAMA_API_URL", "http://127.0.0.1:11434/api/generate"
        )
        self.timeout = int(getattr(config, "OLLAMA_TIMEOUT", 180))

        if self.enabled:
            logger.info("Qwen VLM enabled via Ollama: %s", self.model)
        else:
            logger.info("Qwen VLM disabled by configuration")

    def extract(self, image_path: str) -> Dict[str, Any]:
        """Send a cheque image to Ollama and extract handwriting."""
        request_id = str(uuid.uuid4())[:8]
        if not self.enabled:
            return {
                "status": "DISABLED",
                "fields": {
                    "date": "",
                    "payee_name": "",
                    "amount_words": "",
                    "amount_figures": "",
                    "other_text": "",
                },
            }

        try:
            from PIL import Image
            logger.debug(f"[{request_id}] PIL imported successfully")

            # Resize large scans while preserving their aspect ratio.
            # This helps CPU-only inference and avoids sending huge TIFF files.
            with Image.open(image_path) as source:
                image = source.convert("RGB")
                image.thumbnail((1800, 1800))
                buffer = io.BytesIO()
                logger.debug(f"[{request_id}] Image preprocessing completed")
                image.save(buffer, format="JPEG", quality=92)
                image_b64 = base64.b64encode(buffer.getvalue()).decode("ascii")

            prompt = """
You are extracting fields from a scanned Indian bank cheque.

Read the handwriting visible in the image. Do not invent, complete,
or guess characters that cannot be read. Use an empty string when a
field is missing or illegible.

Return ONLY a JSON object with these keys:
{
  "date": "",
  "payee_name": "",
  "amount_words": "",
  "amount_figures": "",
  "other_text": ""
}

Rules:
- date: transcribe the visible date; do not infer missing digits.
- payee_name: the name written after the cheque's PAY/Pay label.
- amount_words: transcribe the written amount in words.
- amount_figures: transcribe the numeric amount exactly as visible,
  preserving commas and decimal marks where possible.
- other_text: other handwritten content only.
- Keep uncertain text literal; do not silently correct it.
"""

            payload = {
                "model": self.model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0,
                    "num_predict": 300,
                },
            }

            request = urllib.request.Request(
                self.api_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            logger.info(f"[{request_id}] Sending cheque image to Ollama model {self.model}")

            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                api_result = json.loads(response.read().decode("utf-8"))

            generated_text = api_result.get("response", "")
            fields = self._parse_vlm_response(generated_text)

            if not generated_text.strip():
                raise ValueError("Ollama returned an empty response")

            logger.info(f"[{request_id}] Ollama extraction completed successfully")

            return {
                "status": "OK",
                "fields": fields,
                "raw_response": generated_text,
                "model": self.model,
                "confidence": None,
                "confidence_note": (
                    "Ollama response does not provide a calibrated field "
                    "confidence score. Validate fields before accepting them."
                ),
            }

        except Exception as exc:
            logger.exception(f"[{request_id}] Ollama VLM extraction failed at exception handler")
            logger.error(f"[{request_id}] Exception type: {type(exc).__name__}, Message: {str(exc)[:100]}")
            return {
                "status": "ERROR",
                "error": f"{type(exc).__name__}: {exc}",
                "fields": {
                    "date": "",
                    "payee_name": "",
                    "amount_words": "",
                    "amount_figures": "",
                    "other_text": "",
                },
            }

    def _parse_vlm_response(self, response: str) -> Dict[str, str]:
        """Parse JSON returned by Ollama into predictable string fields."""
        try:
            data = json.loads(response)
        except (json.JSONDecodeError, TypeError):
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if not match:
                raise ValueError("Qwen response did not contain valid JSON")
            data = json.loads(match.group(0))

        if not isinstance(data, dict):
            raise ValueError("Qwen response JSON was not an object")

        keys = (
            "date",
            "payee_name",
            "amount_words",
            "amount_figures",
            "other_text",
        )

        return {
            key: str(data.get(key) or "").strip()
            for key in keys
        }
