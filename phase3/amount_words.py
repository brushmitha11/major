import re

ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _below_100(n):
    if n < 20:
        return ONES[n]
    return TENS[n // 10] + (" " + ONES[n % 10] if n % 10 else "")


def _below_1000(n):
    h, rest = divmod(n, 100)
    parts = []
    if h:
        parts.append(ONES[h] + " Hundred")
    if rest:
        parts.append(_below_100(rest))
    return " ".join(parts)


def amount_to_words(figures):
    digits = re.sub(r"\D", "", figures)
    if not digits:
        return ""
    n = int(digits)
    if n == 0:
        return "Zero"
    crore, rest = divmod(n, 10 ** 7)
    lakh, rest = divmod(rest, 10 ** 5)
    thousand, rest = divmod(rest, 1000)
    parts = []
    if crore:
        parts.append(_below_1000(crore) + " Crore")
    if lakh:
        parts.append(_below_100(lakh) + " Lakh")
    if thousand:
        parts.append(_below_100(thousand) + " Thousand")
    if rest:
        parts.append(_below_1000(rest))
    return " ".join(parts)
