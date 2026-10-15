import pytest
from backend.app.extraction.patterns import parse_clean_amount, parse_clean_date, GSTIN_REGEX
from backend.app.extraction.fields import FieldExtractor
from backend.app.schemas.invoice import OCRBox


def test_parse_clean_amount():
    assert parse_clean_amount("₹10,500.50") == 10500.50
    assert parse_clean_amount("Rs. 1,200") == 1200.00
    assert parse_clean_amount("INR 500.25") == 500.25
    assert parse_clean_amount("Total: 999.00") == 999.00
    assert parse_clean_amount("No numbers here") is None


def test_parse_clean_date():
    assert parse_clean_date("25/09/2026") == "2026-09-25"
    assert parse_clean_date("25-09-2026") == "2026-09-25"
    assert parse_clean_date("2026-09-25") == "2026-09-25"
    assert parse_clean_date("25 Sep 2026") == "2026-09-25"
    assert parse_clean_date("25 September 2026") == "2026-09-25"
    assert parse_clean_date("Invalid date string") is None


def test_gstin_regex():
    valid_gstin = "08ABCDE1234F1Z5"
    match = GSTIN_REGEX.search(f"Vendor GSTIN: {valid_gstin} valid")
    assert match is not None
    assert match.group(1).upper() == valid_gstin


def test_spatial_field_extraction():
    # Simulate OCR boxes with spatial coordinates [x_min, y_min, x_max, y_max]
    boxes = [
        OCRBox(text="Acme Industrial Supplies Pvt Ltd", confidence=0.98, bbox=[50, 40, 450, 70]),
        OCRBox(text="TAX INVOICE", confidence=0.99, bbox=[500, 40, 700, 70]),
        OCRBox(text="GSTIN: 07AAAAA0000A1Z5", confidence=0.97, bbox=[50, 80, 350, 105]),
        OCRBox(text="Invoice No:", confidence=0.96, bbox=[50, 130, 160, 155]),
        OCRBox(text="INV-2026-889", confidence=0.95, bbox=[170, 130, 320, 155]),  # to the right
        OCRBox(text="Invoice Date:", confidence=0.95, bbox=[450, 130, 560, 155]),
        OCRBox(text="25/09/2026", confidence=0.96, bbox=[570, 130, 680, 155]),  # to the right
        OCRBox(text="Subtotal", confidence=0.94, bbox=[450, 300, 530, 325]),
        OCRBox(text="10000.00", confidence=0.93, bbox=[580, 300, 680, 325]),  # to the right
        OCRBox(text="CGST", confidence=0.94, bbox=[450, 340, 500, 365]),
        OCRBox(text="900.00", confidence=0.92, bbox=[580, 340, 650, 365]),
        OCRBox(text="SGST", confidence=0.94, bbox=[450, 380, 500, 405]),
        OCRBox(text="900.00", confidence=0.92, bbox=[580, 380, 650, 405]),
        OCRBox(text="Grand Total", confidence=0.98, bbox=[450, 430, 560, 460]),
        OCRBox(text="11800.00", confidence=0.97, bbox=[580, 430, 680, 460]),
    ]

    extractor = FieldExtractor(boxes)
    data, conf = extractor.extract_all()

    assert data.vendor_name == "Acme Industrial Supplies Pvt Ltd"
    assert data.invoice_number == "INV-2026-889"
    assert data.invoice_date == "2026-09-25"
    assert data.gstin == "07AAAAA0000A1Z5"
    assert data.subtotal == 10000.00
    assert data.cgst == 900.00
    assert data.sgst == 900.00
    assert data.total == 11800.00
    assert conf["total"] == 0.97
