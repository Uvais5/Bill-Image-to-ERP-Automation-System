from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from ..config import settings
from ..extraction.patterns import GSTIN_REGEX
from ..schemas.invoice import InvoiceData


def validate_required_fields(data: InvoiceData) -> List[str]:
    """Ensures mandatory ERP invoice fields are present."""
    errors = []
    if not data.vendor_name or not data.vendor_name.strip():
        errors.append("Missing required field: Vendor Name")
    if not data.invoice_number or not data.invoice_number.strip():
        errors.append("Missing required field: Invoice Number")
    if not data.invoice_date or not data.invoice_date.strip():
        errors.append("Missing required field: Invoice Date")
    if data.total is None or data.total <= 0:
        errors.append("Missing or invalid required field: Total Amount")
    return errors


def validate_date(date_str: Optional[str]) -> Tuple[List[str], List[str]]:
    """Validates invoice date sanity (format and range)."""
    errors = []
    warnings = []
    if not date_str:
        return errors, warnings

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        now = datetime.now()
        # Cannot be more than 1 day in the future
        if dt > now + timedelta(days=1):
            warnings.append(f"Invoice date {date_str} is in the future")
        # Cannot be older than 5 years
        if dt < now - timedelta(days=365 * 5):
            warnings.append(f"Invoice date {date_str} is older than 5 years")
    except ValueError:
        errors.append(f"Invalid date format for '{date_str}'. Expected YYYY-MM-DD.")

    return errors, warnings


def validate_gstin(gstin: Optional[str]) -> Tuple[List[str], List[str]]:
    """Validates 15-character GSTIN structure."""
    errors = []
    warnings = []
    if not gstin:
        warnings.append("GSTIN is not present on invoice")
        return errors, warnings

    cleaned = gstin.strip().upper()
    if len(cleaned) != 15:
        errors.append(f"Invalid GSTIN length ({len(cleaned)} chars, expected 15)")
    elif not GSTIN_REGEX.match(cleaned):
        errors.append(f"Invalid GSTIN structure: '{cleaned}'")

    return errors, warnings


def validate_amounts_and_taxes(data: InvoiceData) -> Tuple[List[str], List[str]]:
    """Reconciles subtotal, taxes (CGST, SGST, IGST), and total with tolerance."""
    errors = []
    warnings = []

    if data.total is not None and data.total < 0:
        errors.append(f"Total amount cannot be negative: {data.total}")

    if data.subtotal is not None and data.total is not None:
        if data.subtotal > data.total + settings.AMOUNT_TOLERANCE:
            errors.append(
                f"Subtotal ({data.subtotal:.2f}) cannot exceed Total ({data.total:.2f})"
            )

        cgst = data.cgst or 0.0
        sgst = data.sgst or 0.0
        igst = data.igst or 0.0

        # Intrastate check: CGST and SGST should typically match if both present
        if data.cgst is not None and data.sgst is not None:
            if abs(data.cgst - data.sgst) > settings.AMOUNT_TOLERANCE:
                warnings.append(
                    f"CGST ({data.cgst:.2f}) and SGST ({data.sgst:.2f}) amounts differ"
                )

        # Expected total reconciliation
        tax_sum = cgst + sgst + igst
        expected_total = round(data.subtotal + tax_sum, 2)
        diff = abs(expected_total - data.total)

        if tax_sum > 0:
            if expected_total > data.total + settings.AMOUNT_TOLERANCE:
                errors.append(
                    f"Amount error: Subtotal ({data.subtotal:.2f}) + Taxes ({tax_sum:.2f}) = {expected_total:.2f} exceeds Total ({data.total:.2f})"
                )
            elif expected_total < data.total - settings.AMOUNT_TOLERANCE:
                warnings.append(
                    f"Note: Taxable Subtotal ({data.subtotal:.2f}) + Taxes ({tax_sum:.2f}) = {expected_total:.2f}. Total ({data.total:.2f}) includes ₹{diff:.2f} in non-taxable / exempt charges."
                )

    return errors, warnings


def validate_confidences(
    confidence_map: Dict[str, float]
) -> List[str]:
    """Generates user warnings for fields with low OCR confidence scores."""
    warnings = []
    for field, score in confidence_map.items():
        if score > 0 and score < settings.OCR_CONFIDENCE_THRESHOLD_MEDIUM:
            clean_field = field.replace("_", " ").title()
            warnings.append(f"Low OCR confidence ({score:.0%}) for {clean_field}. Please verify.")
    return warnings
