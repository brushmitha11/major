from datetime import datetime
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
        # Require an explicit MICR label; never guess from arbitrary numbers.
        text = text or ""
        for line in text.splitlines():
            if not re.search(r"\bMICR\b", line, re.IGNORECASE):
                continue

            candidates = re.findall(r"(?<!\d)(\d(?:[\s-]*\d){8})(?!\d)", line)
            for candidate in candidates:
                micr = re.sub(r"\D", "", candidate)
                if len(micr) == 9:
                    self.log_extraction("micr_code", "labelled_micr", micr, 0.90)
                    return micr, 0.90

        self.log_extraction("micr_code", "no_explicit_micr_label", None, 0.0)
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
        # Only accept a number explicitly associated with an account label.
        text = text or ""
        patterns = [
            r"(?im)^.*?\bA\s*/?\s*C\s*(?:NO|NUMBER)?\.?\s*[:\-]?\s*([0-9][0-9\s-]{5,24})",
            r"(?im)^.*?\bACCOUNT\s*(?:NO|NUMBER|NUM)\.?\s*[:\-]?\s*([0-9][0-9\s-]{5,24})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                candidate = re.sub(r"\D", "", match.group(1))
                if 6 <= len(candidate) <= 18:
                    self.log_extraction("account_number", "labelled_account", candidate, 0.90)
                    return candidate, 0.90

        self.log_extraction("account_number", "no_explicit_account_label", None, 0.0)
        return None, 0.0

    def extract_date(self, text):
        # Validate calendar dates; do not accept impossible dates.
        text = text or ""
        patterns = [
            r"(?<!\d)(\d{2})[/-](\d{2})[/-](\d{4})(?!\d)",
            r"(?<!\d)(\d{4})[/-](\d{2})[/-](\d{2})(?!\d)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                parts = match.groups()
                candidates = ["/".join(parts)]
                if len(parts[0]) == 4:
                    candidates.append(f"{parts[2]}/{parts[1]}/{parts[0]}")
                for candidate in candidates:
                    for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y-%m-%d"):
                        try:
                            parsed = datetime.strptime(candidate, fmt)
                            value = parsed.strftime("%d/%m/%Y")
                            self.log_extraction("date", "validated_date", value, 0.95)
                            return value, 0.95
                        except ValueError:
                            pass

        self.log_extraction("date", "no_valid_date", None, 0.0)
        return None, 0.0

    def extract_amount_figures(self, text):
        # Prefer explicit amount labels or currency markers. Avoid IDs, MICR,
        # IFSC, account numbers, and date lines.
        text = text or ""
        amount_re = re.compile(
            r"(?<![A-Z0-9])(?:\u20B9|RS\.?\s*)\s*([0-9][0-9,]*(?:\.\d{1,2})?)(?![A-Z0-9])",
            re.IGNORECASE
        )
        number_re = re.compile(
            r"(?<![A-Z0-9])([0-9]{1,3}(?:,[0-9]{3})+(?:\.\d{1,2})?|[0-9]{2,}(?:\.\d{1,2}))(?![A-Z0-9])",
            re.IGNORECASE
        )
        lines = text.splitlines()

        # Highest priority: amount explicitly labelled on its line.
        for line in lines:
            if re.search(r"\b(AMOUNT|RUPEES|RS\.?|INR)\b|\u20B9", line, re.IGNORECASE):
                if re.search(r"\b(MICR|IFSC|A/C|ACCOUNT|CHEQUE|CHQ|DATE|REFERENCE|CUSTOMER)\b",
                             line, re.IGNORECASE):
                    continue
                matches = list(amount_re.finditer(line))
                if matches:
                    value = matches[-1].group(1).replace(",", "")
                    self.log_extraction("amount_figures", "labelled_amount", value, 0.95)
                    return value, 0.95
                # An amount-labelled line may contain a plain numeric value.
                matches = list(number_re.finditer(line))
                if matches:
                    value = matches[-1].group(1).replace(",", "")
                    self.log_extraction("amount_figures", "amount_context", value, 0.85)
                    return value, 0.85

        # Next: currency-marked values anywhere outside identifier lines.
        for line in lines:
            if re.search(r"\b(MICR|IFSC|A/C|ACCOUNT|CHEQUE|CHQ|DATE|REFERENCE|CUSTOMER)\b",
                         line, re.IGNORECASE):
                continue
            matches = list(amount_re.finditer(line))
            if matches:
                value = matches[-1].group(1).replace(",", "")
                self.log_extraction("amount_figures", "currency_marker", value, 0.90)
                return value, 0.90

        # Conservative fallback: decimal amounts on unlabelled lines only.
        for line in lines:
            if re.search(r"\b(MICR|IFSC|A/C|ACCOUNT|CHEQUE|CHQ|DATE|REFERENCE|CUSTOMER)\b",
                         line, re.IGNORECASE):
                continue
            matches = list(re.finditer(
                r"(?<![\d/.-])(\d{1,3}(?:,\d{3})+(?:\.\d{2})|\d{2,}(?:\.\d{2}))(?!\d)",
                line
            ))
            if matches:
                value = matches[-1].group(1).replace(",", "")
                self.log_extraction("amount_figures", "unlabelled_decimal_candidate", value, 0.60)
                return value, 0.60

        self.log_extraction("amount_figures", "no_reliable_amount", None, 0.0)
        return None, 0.0

    def extract_amount_words(self, text):
        # Extract number words only from a labelled amount-in-words line.
        text = text or ""
        word = (
            r"(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|"
            r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|"
            r"eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|"
            r"eighty|ninety|hundred|thousand|lakh|lakhs|million|crore|"
            r"crores|and|only|rupee|rupees)"
        )
        for line in text.splitlines():
            # Avoid treating a numeric AMOUNT line as amount-in-words.
            if not re.search(
                r"\b(?:RUPEES?|AMOUNT\s+IN\s+WORDS)\b",
                line,
                re.IGNORECASE,
            ):
                continue

            matches = re.findall(word, line, re.IGNORECASE)
            if matches:
                value = " ".join(matches).upper()
                value = re.sub(r"\bRUPEE\b", "RUPEES", value)
                self.log_extraction("amount_words", "amount_context", value, 0.80)
                return value, 0.80

        self.log_extraction("amount_words", "no_amount_words_context", None, 0.0)
        return None, 0.0

    def extract_payee_name(self, text):
        # Read the name after a payee label, preferably on the same line.
        text = text or ""
        lines = text.splitlines()
        label = re.compile(
            r"\b(?:PAY\s+TO(?:\s+THE)?\s+ORDER\s+OF|PAY\s+TO|PAYEE)\b\s*[:\-]?\s*(.*)",
            re.IGNORECASE
        )
        stop = re.compile(
            r"\b(?:RUPEES?|AMOUNT|DATE|CHEQUE|CHQ|MICR|IFSC|A/C|ACCOUNT|"
            r"BANK|BEARER|SIGNATURE|RS\.?)\b",
            re.IGNORECASE
        )

        for index, line in enumerate(lines):
            match = label.search(line)
            if not match:
                continue

            candidate = match.group(1).strip(" :-\t")
            if not candidate:
                # Some OCR engines place the payee on the next line.
                for next_line in lines[index + 1:index + 3]:
                    if not next_line.strip():
                        continue
                    if stop.search(next_line):
                        break
                    candidate = next_line.strip()
                    break

            candidate = stop.split(candidate, maxsplit=1)[0].strip(" :-\t,.;")
            candidate = re.sub(r"\s+", " ", candidate)
            if candidate and re.search(r"[A-Za-z]", candidate) and len(candidate) <= 100:
                self.log_extraction("payee_name", "payee_label", candidate, 0.90)
                return candidate, 0.90

        self.log_extraction("payee_name", "no_payee_label", None, 0.0)
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
