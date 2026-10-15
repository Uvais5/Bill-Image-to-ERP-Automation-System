import re
from datetime import datetime
from typing import Optional, Tuple

# GSTIN Regex Pattern (15 chars Indian GST format)
GSTIN_REGEX = re.compile(
    r"\b([0-3][0-9][A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b",
    re.IGNORECASE,
)

# Date Regex Patterns & Formats
DATE_PATTERNS = [
    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    (re.compile(r"\b(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})\b"), "%d/%m/%Y"),
    # YYYY-MM-DD or YYYY/MM/DD
    (re.compile(r"\b(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})\b"), "%Y-%m-%d"),
    # DD Mon YYYY / DD Month YYYY (e.g. 25 Sep 2026, 25-September-2026)
    (
        re.compile(
            r"\b(\d{1,2})[\s\-.](Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s\-.](\d{4})\b",
            re.IGNORECASE,
        ),
        "text_date",
    ),
]

# Numeric Amount Pattern
AMOUNT_REGEX = re.compile(
    r"(?:₹|Rs\.?|INR)?\s*([0-9]{1,3}(?:,[0-9]{2,3})+(?:\.[0-9]{1,2})?|[0-9]+(?:\.[0-9]{1,2})?)",
    re.IGNORECASE,
)

# Field Keyword lists for fuzzy/exact matching
KEYWORDS = {
    "total": [
        "grand total",
        "total amount",
        "net payable",
        "total payable",
        "net amount",
        "invoice total",
        "total (inr)",
        "total inr",
        "total value",
        "final total",
        "total",
    ],
    "subtotal": [
        "sub total",
        "subtotal",
        "taxable value",
        "taxable amount",
        "base amount",
        "gross amount",
        "amount before tax",
        "net taxable",
    ],
    "cgst": [
        "cgst amount",
        "cgst amt",
        "cgst",
        "central gst",
        "central tax",
    ],
    "sgst": [
        "sgst amount",
        "sgst amt",
        "sgst",
        "state gst",
        "state tax",
        "utgst",
    ],
    "igst": [
        "igst amount",
        "igst amt",
        "igst",
        "integrated gst",
        "integrated tax",
    ],
    "invoice_number": [
        "tax invoice no",
        "invoice no.",
        "invoice no",
        "invoice number",
        "invoice #",
        "inv no.",
        "inv no",
        "inv #",
        "bill no.",
        "bill no",
        "bill number",
        "bill #",
        "receipt no",
        "doc no",
    ],
    "invoice_date": [
        "invoice date",
        "bill date",
        "date of issue",
        "dated",
        "inv date",
        "issue date",
        "date",
    ],
    "vendor": [
        "sold by",
        "supplier name",
        "supplier",
        "vendor name",
        "vendor",
        "from:",
        "billed by",
    ],
}


def parse_clean_amount(text: str) -> Optional[float]:
    """Extracts a valid numeric float from text containing potential currency symbols/commas."""
    text = text.replace("₹", "").replace("Rs.", "").replace("Rs", "").replace("INR", "").strip()
    match = AMOUNT_REGEX.search(text)
    if not match:
        return None
    val_str = match.group(1).replace(",", "").strip()
    try:
        val = float(val_str)
        return round(val, 2)
    except ValueError:
        return None


def parse_clean_date(text: str) -> Optional[str]:
    """Extracts and normalizes a date string into standard ISO YYYY-MM-DD."""
    for pattern, date_fmt in DATE_PATTERNS:
        match = pattern.search(text)
        if match:
            if date_fmt == "text_date":
                day, month_str, year = match.groups()
                # Parse standard month name
                for fmt in ["%d %b %Y", "%d %B %Y"]:
                    try:
                        dt = datetime.strptime(f"{day} {month_str} {year}", fmt)
                        return dt.strftime("%Y-%m-%d")
                    except ValueError:
                        pass
            elif date_fmt == "%d/%m/%Y":
                day, month, year = match.groups()
                try:
                    dt = datetime(int(year), int(month), int(day))
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
            elif date_fmt == "%Y-%m-%d":
                year, month, day = match.groups()
                try:
                    dt = datetime(int(year), int(month), int(day))
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    pass
    return None
