from typing import Dict, Optional
from ..schemas.invoice import InvoiceData, ValidationResult
from .rules import (
    validate_amounts_and_taxes,
    validate_confidences,
    validate_date,
    validate_gstin,
    validate_required_fields,
)


class InvoiceValidator:
    def validate(
        self, data: InvoiceData, confidence_map: Optional[Dict[str, float]] = None
    ) -> ValidationResult:
        """
        Runs comprehensive validation across required fields, dates, GSTIN, amount reconciliation, and confidence signals.
        """
        errors = []
        warnings = []

        # 1. Required fields
        req_errors = validate_required_fields(data)
        errors.extend(req_errors)

        # 2. Date sanity
        date_errors, date_warnings = validate_date(data.invoice_date)
        errors.extend(date_errors)
        warnings.extend(date_warnings)

        # 3. GSTIN structure
        gstin_errors, gstin_warnings = validate_gstin(data.gstin)
        errors.extend(gstin_errors)
        warnings.extend(gstin_warnings)

        # 4. Amount and Tax arithmetic
        amt_errors, amt_warnings = validate_amounts_and_taxes(data)
        errors.extend(amt_errors)
        warnings.extend(amt_warnings)

        # 5. Low confidence warnings
        if confidence_map:
            conf_warnings = validate_confidences(confidence_map)
            warnings.extend(conf_warnings)

        is_valid = len(errors) == 0

        return ValidationResult(
            valid=is_valid,
            warnings=warnings,
            errors=errors,
        )


invoice_validator = InvoiceValidator()
