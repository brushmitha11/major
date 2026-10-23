import re
from typing import Dict, Tuple

FIELD_ORDER = ["bank_name", "cheque_number", "micr_code", "account_number", "date", "payee_name", "amount_figures", "amount_words", "ifsc_code"]

IFSC_BANKS = {
    "ICIC": "ICICI BANK", "UTIB": "AXIS BANK", "SYNB": "SYNDICATE BANK", "CNRB": "CANARA BANK",
    "SBIN": "STATE BANK OF INDIA", "HDFC": "HDFC BANK", "UBIN": "UNION BANK OF INDIA",
    "PUNB": "PUNJAB NATIONAL BANK", "IDIB": "INDIAN BANK", "BARB": "BANK OF BARODA",
}

class FieldExtractor:
    """Extract cheque fields without inventing missing values."""

    def __init__(self, metadata=None):
        self.metadata = metadata or {}
        self.extraction_log = []

    def log_extraction(self, field, method, value, confidence):
        self.extraction_log.append({"field": field, "method": method, "value": value, "confidence": confidence})

    def extract_ifsc_code(self, text):
        pattern = r"\b([A-Z]{4}0[A-Z0-9]{6})\b"
        m = re.search(pattern, text or "")
        if m:
            self.log_extraction("ifsc_code", "regex", m.group(1), 0.95)
            return m.group(1), 0.95
        return None, 0.0

    def extract_bank_name(self, text, ifsc_code=None, meta=None):
        if ifsc_code:
            bank = IFSC_BANKS.get(ifsc_code[:4])
            if bank:
                self.log_extraction("bank_name", "ifsc_lookup", bank, 0.95)
                return bank, 0.95

        pattern = r"\b([A-Z]{2,}\s+BANK(?:\s+(?:LTD|LIMITED|OF\s+INDIA))?)\b"
        m = re.search(pattern, text or "", re.IGNORECASE)
        if m:
            self.log_extraction("bank_name", "regex", m.group(1), 0.85)
            return m.group(1), 0.85

        if meta and "bank" in meta:
            bank = meta.get("bank", "").upper()
            if bank:
                self.log_extraction("bank_name", "metadata", bank, 0.99)
                return bank, 0.99

        self.log_extraction("bank_name", "unavailable", None, 0.0)
        return None, 0.0

    def extract_micr_code(self, text):
        pattern = r"(?<!\d)(\d{6})[\s\W]*(\d{3})[\s\W]*(\d{3})[\s\W]*(\d{3})(?!\d)"
        m = re.search(pattern, text or "")
        if m:
            micr = f"{m.group(2)}{m.group(3)}{m.group(4)}"
            if len(micr) == 9:
                self.log_extraction("micr_code", "regex", micr, 0.90)
                return micr, 0.90
        return None, 0.0

    def extract_cheque_number(self, text, micr_code=None):
        if micr_code and len(micr_code) == 9:
            m = re.search(r"(?<!\d)(\d{6})[\s\W]*\d{3}[\s\W]*\d{3}[\s\W]*\d{3}", text or "")
            if m:
                self.log_extraction("cheque_number", "from_micr", m.group(1), 0.95)
                return m.group(1), 0.95

        pattern = r"(?<!\d)(\d{6})(?!\d)"
        matches = re.findall(pattern, text or "")
        if matches:
            self.log_extraction("cheque_number", "regex", matches[0], 0.85)
            return matches[0], 0.85

        return None, 0.0

    def extract_account_number(self, text):
        patterns = [r"(?:A/?C\s*NO\.?|ACCOUNT)\s*:?\s*([0-9\s\-]{6,})", r"(\d{6,18})"]

        for pattern in patterns:
            m = re.search(pattern, text or "", re.IGNORECASE)
            if m:
                account = re.sub(r"\D", "", m.group(1))
                if 6 <= len(account) <= 18:
                    self.log_extraction("account_number", "regex", account, 0.90)
                    return account, 0.90

        return None, 0.0

    def extract_date(self, text):
        pattern = r"(\d{2})[/-](\d{2})[/-](\d{4})"
        m = re.search(pattern, text or "")
        if m:
            self.log_extraction("date", "regex", m.group(0), 0.85)
            return m.group(0), 0.85

        self.log_extraction("date", "unavailable", None, 0.0)
        return None, 0.0

    def extract_amount_figures(self, text):
        patterns = [r"₹\s*([0-9,]+(?:\.\d{1,2})?)", r"Rs\.?\s*([0-9,]+(?:\.\d{1,2})?)", r"([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]{2})?)"]

        for pattern in patterns:
            matches = re.findall(pattern, text or "")
            if matches:
                amount = matches[-1] if len(matches) > 1 else matches[0]
                self.log_extraction("amount_figures", "regex", amount, 0.85)
                return amount, 0.85

        return None, 0.0

    def extract_amount_words(self, text):
        words_pattern = r"((?:hundred|thousand|lakh|crore)\s+)?(?:and\s+)?(?:hundred|thousand|lakh|crore|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)+(?:\s+(?:hundred|thousand|lakh|crore|rupees?))?"

        m = re.search(words_pattern, text or "", re.IGNORECASE)
        if m:
            self.log_extraction("amount_words", "regex", m.group(0), 0.80)
            return m.group(0), 0.80

        self.log_extraction("amount_words", "unavailable", None, 0.0)
        return None, 0.0

    def extract_payee_name(self, text):
        cleaned = re.sub(r"(?:PAY|TO|BEARER|ORDER|A/C|NO\.|ACCOUNT|DATE|AMOUNT)", "", text or "", flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        if cleaned and len(cleaned) > 2:
            self.log_extraction("payee_name", "filtered_text", cleaned, 0.75)
            return cleaned, 0.75

        return None, 0.0

    def extract_all_fields(self, ocr_text, meta=None):
        """Extract all fields with zero-blank guarantee."""
        results = {}
        confidence = {}

        ifsc_value, ifsc_conf = self.extract_ifsc_code(ocr_text)
        results["ifsc_code"] = ifsc_value
        confidence["ifsc_code"] = ifsc_conf

        results["bank_name"], confidence["bank_name"] = self.extract_bank_name(ocr_text, ifsc_value, meta)
        results["micr_code"], confidence["micr_code"] = self.extract_micr_code(ocr_text)
        results["cheque_number"], confidence["cheque_number"] = self.extract_cheque_number(ocr_text, results["micr_code"])
        results["account_number"], confidence["account_number"] = self.extract_account_number(ocr_text)
        results["date"], confidence["date"] = self.extract_date(ocr_text)
        results["amount_figures"], confidence["amount_figures"] = self.extract_amount_figures(ocr_text)
        results["amount_words"], confidence["amount_words"] = self.extract_amount_words(ocr_text)
        results["payee_name"], confidence["payee_name"] = self.extract_payee_name(ocr_text)

        # Missing extraction must remain missing, never fabricated.
        for field in FIELD_ORDER:
            if results.get(field) is None or results.get(field) == "":
                results[field] = None
                confidence[field] = 0.0

        return {
            "fields": {k: results[k] for k in FIELD_ORDER},
            "confidence": confidence,
            "extraction_log": self.extraction_log,
            "has_blanks": any(v is None or v == "" for v in results.values())
        }
