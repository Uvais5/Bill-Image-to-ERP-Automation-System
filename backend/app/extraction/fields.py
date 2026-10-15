import re
from typing import Dict, List, Optional, Tuple
from ..schemas.invoice import InvoiceData, OCRBox
from .patterns import (
    GSTIN_REGEX,
    KEYWORDS,
    parse_clean_amount,
    parse_clean_date,
)
from .spatial import find_box_below, find_box_to_right


class FieldExtractor:
    def __init__(self, boxes: List[OCRBox]):
        self.boxes = sorted(boxes, key=lambda b: (b.bbox[1], b.bbox[0]))

    def extract_gstin(self) -> Tuple[Optional[str], float]:
        """Extracts GSTIN using regex pattern matching across all OCR boxes."""
        for box in self.boxes:
            match = GSTIN_REGEX.search(box.text)
            if match:
                return match.group(1).upper(), box.confidence
        return None, 0.0

    def extract_invoice_number(self) -> Tuple[Optional[str], float]:
        """Extracts invoice number using label identification & spatial proximity."""
        # 1. Look for explicit keyword patterns (with or without spaces/colons)
        kw_regex = re.compile(
            r"(?:tax\s+)?(?:invoice|bill|receipt)\s*(?:no\.?|num\.?|number|#)?\s*[:#\s\-]\s*([0-9A-Za-z][0-9A-Za-z\-_/]{2,})|(?:invoiceno|billno|invno)\s*[:#\-]?\s*([0-9A-Za-z][0-9A-Za-z\-_/]{2,})",
            re.IGNORECASE,
        )
        for box in self.boxes:
            match = kw_regex.search(box.text)
            if match:
                candidate = (match.group(1) or match.group(2) or "").strip()
                if candidate and candidate.lower() not in {"invoice", "tax", "bill", "date", "no"}:
                    return candidate, box.confidence

        # 2. Check spatial neighbors
        for box in self.boxes:
            lower_text = box.text.lower()
            for kw in KEYWORDS["invoice_number"]:
                if kw in lower_text:
                    right_box = find_box_to_right(box, self.boxes)
                    if right_box and right_box.text.strip():
                        token = right_box.text.strip().split()[0].strip(":#-")
                        if token and token.lower() not in {"invoice", "date", "bill"}:
                            return token, min(box.confidence, right_box.confidence)
                    
                    below_box = find_box_below(box, self.boxes)
                    if below_box and below_box.text.strip():
                        token = below_box.text.strip().split()[0].strip(":#-")
                        if token and token.lower() not in {"invoice", "date", "bill"}:
                            return token, min(box.confidence, below_box.confidence)

        # 3. Fallback: regex for alphanumeric invoice IDs starting with INV- or BILL-
        inv_pattern = re.compile(r"\b(?:INV|BILL)[-_#/]?([0-9][0-9A-Z\-_/]{2,})\b", re.IGNORECASE)
        for box in self.boxes:
            match = inv_pattern.search(box.text)
            if match:
                return match.group(0), box.confidence

        return None, 0.0

    def extract_invoice_date(self) -> Tuple[Optional[str], float]:
        """Extracts date prioritizing proximity to date keywords, falling back to any date found."""
        # 1. Proximity to date keywords
        for box in self.boxes:
            lower_text = box.text.lower()
            for kw in KEYWORDS["invoice_date"]:
                if kw in lower_text:
                    # Inline
                    parsed = parse_clean_date(box.text)
                    if parsed:
                        return parsed, box.confidence
                    
                    # Right neighbor
                    right_box = find_box_to_right(box, self.boxes)
                    if right_box:
                        parsed = parse_clean_date(right_box.text)
                        if parsed:
                            return parsed, min(box.confidence, right_box.confidence)
                    
                    # Below neighbor
                    below_box = find_box_below(box, self.boxes)
                    if below_box:
                        parsed = parse_clean_date(below_box.text)
                        if parsed:
                            return parsed, min(box.confidence, below_box.confidence)

        # 2. Fallback: scan all boxes
        for box in self.boxes:
            parsed = parse_clean_date(box.text)
            if parsed:
                return parsed, box.confidence

        return None, 0.0

    def extract_vendor_name(self) -> Tuple[Optional[str], float]:
        """Extracts vendor name from invoice header or labeled sections."""
        ignore_keywords = [
            "tax invoice", "invoice", "bill of supply", "receipt", "cash memo",
            "original", "duplicate", "triplicate", "gstin", "place of supply",
            "date", "total", "amount", "hsn", "qty", "rate"
        ]

        # 1. Check explicit label (e.g., "Supplier: Acme Corp", "Sold By: XYZ", "From: ...")
        vendor_label_regex = re.compile(
            r"^(?:supplier\s+name|vendor\s+name|sold\s+by|billed\s+by|supplier|vendor|from)\s*[:#-]\s*(.+)$",
            re.IGNORECASE,
        )
        for box in self.boxes:
            match = vendor_label_regex.match(box.text.strip())
            if match:
                val = match.group(1).strip()
                if len(val) > 2 and not any(ig in val.lower() for ig in ignore_keywords):
                    return val, box.confidence

            # Standalone label box (e.g. "Supplier:" or "Sold By")
            lower_clean = box.text.strip().lower()
            for kw in ["supplier name", "vendor name", "sold by", "billed by", "supplier:", "vendor:", "from:"]:
                if lower_clean == kw or lower_clean == kw.rstrip(":"):
                    right_box = find_box_to_right(box, self.boxes)
                    if right_box and len(right_box.text.strip()) > 2 and not any(ig in right_box.text.lower() for ig in ignore_keywords):
                        return right_box.text.strip(), min(box.confidence, right_box.confidence)

                    below_box = find_box_below(box, self.boxes)
                    if below_box and len(below_box.text.strip()) > 2 and not any(ig in below_box.text.lower() for ig in ignore_keywords):
                        return below_box.text.strip(), min(box.confidence, below_box.confidence)

        # 2. Header heuristic (Company name in top 25% of the document)
        if self.boxes:
            top_boxes = [b for b in self.boxes if b.bbox[1] < max(300, self.boxes[-1].bbox[3] * 0.25)]
            for b in top_boxes:
                cleaned = b.text.strip()
                cleaned_lower = cleaned.lower()
                if any(ig in cleaned_lower for ig in ignore_keywords) or GSTIN_REGEX.search(cleaned):
                    continue
                if len(cleaned) > 2 and not parse_clean_amount(cleaned):
                    return cleaned, b.confidence

        return None, 0.0

    def _extract_amount_for_keywords(
        self, keyword_list: List[str], exclude_keywords: Optional[List[str]] = None
    ) -> Tuple[Optional[float], float]:
        """Helper to find amount spatially linked to specific label keywords."""
        sorted_kws = sorted(keyword_list, key=len, reverse=True)
        for kw in sorted_kws:
            kw_pattern = re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE)
            for box in self.boxes:
                lower_text = box.text.lower()
                if exclude_keywords and any(ex in lower_text for ex in exclude_keywords):
                    continue
                match = kw_pattern.search(lower_text)
                if match:
                    # 1. Inline
                    after_kw = box.text[match.end():]
                    amt = parse_clean_amount(after_kw)
                    if amt is not None:
                        return amt, box.confidence

                    # 2. Right neighbor
                    right_box = find_box_to_right(box, self.boxes)
                    if right_box:
                        amt = parse_clean_amount(right_box.text)
                        if amt is not None:
                            return amt, min(box.confidence, right_box.confidence)

                    # 3. Below neighbor
                    below_box = find_box_below(box, self.boxes)
                    if below_box:
                        amt = parse_clean_amount(below_box.text)
                        if amt is not None:
                            return amt, min(box.confidence, below_box.confidence)

        return None, 0.0

    def extract_subtotal(self) -> Tuple[Optional[float], float]:
        return self._extract_amount_for_keywords(KEYWORDS["subtotal"])

    def extract_cgst(self) -> Tuple[Optional[float], float]:
        return self._extract_amount_for_keywords(KEYWORDS["cgst"])

    def extract_sgst(self) -> Tuple[Optional[float], float]:
        return self._extract_amount_for_keywords(KEYWORDS["sgst"])

    def extract_igst(self) -> Tuple[Optional[float], float]:
        return self._extract_amount_for_keywords(KEYWORDS["igst"])

    def extract_total(self) -> Tuple[Optional[float], float]:
        # Search specifically excluding subtotal / base keywords
        total_val, conf = self._extract_amount_for_keywords(
            KEYWORDS["total"], exclude_keywords=["subtotal", "sub total", "taxable"]
        )
        if total_val is not None:
            return total_val, conf

        # Fallback: largest amount on invoice
        amounts: List[Tuple[float, float]] = []
        for box in self.boxes:
            amt = parse_clean_amount(box.text)
            if amt is not None:
                amounts.append((amt, box.confidence))
        if amounts:
            max_amt, max_conf = max(amounts, key=lambda item: item[0])
            return max_amt, max_conf

        return None, 0.0

    def extract_all(self) -> Tuple[InvoiceData, Dict[str, float]]:
        """Orchestrates extraction of all fields and returns structured data & confidence map."""
        vendor, c_vendor = self.extract_vendor_name()
        inv_no, c_inv = self.extract_invoice_number()
        inv_date, c_date = self.extract_invoice_date()
        gstin, c_gstin = self.extract_gstin()
        subtotal, c_sub = self.extract_subtotal()
        cgst, c_cgst = self.extract_cgst()
        sgst, c_sgst = self.extract_sgst()
        igst, c_igst = self.extract_igst()
        total, c_tot = self.extract_total()

        invoice_data = InvoiceData(
            vendor_name=vendor,
            invoice_number=inv_no,
            invoice_date=inv_date,
            gstin=gstin,
            subtotal=subtotal,
            cgst=cgst,
            sgst=sgst,
            igst=igst,
            total=total,
        )

        confidence_map = {
            "vendor_name": round(c_vendor, 3),
            "invoice_number": round(c_inv, 3),
            "invoice_date": round(c_date, 3),
            "gstin": round(c_gstin, 3),
            "subtotal": round(c_sub, 3),
            "cgst": round(c_cgst, 3),
            "sgst": round(c_sgst, 3),
            "igst": round(c_igst, 3),
            "total": round(c_tot, 3),
        }

        return invoice_data, confidence_map
