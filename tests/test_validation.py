import pytest
from backend.app.schemas.invoice import InvoiceData
from backend.app.validation.validator import InvoiceValidator


def test_validation_valid_invoice():
    validator = InvoiceValidator()
    data = InvoiceData(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        invoice_date="2026-09-25",
        gstin="07AAAAA0000A1Z5",
        subtotal=10000.0,
        cgst=900.0,
        sgst=900.0,
        total=11800.0,
    )
    conf = {"vendor_name": 0.95, "total": 0.98}
    result = validator.validate(data, conf)

    assert result.valid is True
    assert len(result.errors) == 0


def test_validation_missing_required_fields():
    validator = InvoiceValidator()
    data = InvoiceData(
        vendor_name="",
        invoice_number=None,
        invoice_date=None,
        total=None,
    )
    result = validator.validate(data)

    assert result.valid is False
    assert any("Vendor Name" in e for e in result.errors)
    assert any("Invoice Number" in e for e in result.errors)
    assert any("Invoice Date" in e for e in result.errors)
    assert any("Total Amount" in e for e in result.errors)


def test_validation_amount_tax_mismatch():
    validator = InvoiceValidator()
    # 10000 + 900 + 900 = 11800, but total is 10500 (Subtotal + tax exceeds total)
    data = InvoiceData(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        invoice_date="2026-09-25",
        gstin="07AAAAA0000A1Z5",
        subtotal=10000.0,
        cgst=900.0,
        sgst=900.0,
        total=10500.0,
    )
    result = validator.validate(data)

    assert result.valid is False
    assert any("Amount error" in e for e in result.errors)


def test_validation_invalid_gstin():
    validator = InvoiceValidator()
    data = InvoiceData(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        invoice_date="2026-09-25",
        gstin="INVALID_GSTIN_123",
        subtotal=1000.0,
        total=1000.0,
    )
    result = validator.validate(data)

    assert result.valid is False
    assert any("Invalid GSTIN" in e for e in result.errors)


def test_validation_low_confidence_warning():
    validator = InvoiceValidator()
    data = InvoiceData(
        vendor_name="Acme Corp",
        invoice_number="INV-001",
        invoice_date="2026-09-25",
        gstin="07AAAAA0000A1Z5",
        total=1000.0,
    )
    # Low confidence on vendor name
    conf = {"vendor_name": 0.45, "total": 0.95}
    result = validator.validate(data, conf)

    assert result.valid is True
    assert len(result.warnings) > 0
    assert any("Low OCR confidence" in w for w in result.warnings)
