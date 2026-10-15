import cv2
import numpy as np
import pytest
from backend.app.ocr.engine import ocr_engine
from backend.app.ocr.preprocessing import decode_image, preprocess_pipeline, resize_image_if_needed


def create_synthetic_test_invoice() -> bytes:
    """Generates a small test image containing rendered text in memory."""
    # Create white canvas
    img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    # Draw simple text
    cv2.putText(img, "TAX INVOICE", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Vendor: XYZ Logistics", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "Invoice No: INV-999", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "Total: 5000", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


def test_decode_and_preprocessing():
    img_bytes = create_synthetic_test_invoice()
    decoded = decode_image(img_bytes)
    assert decoded is not None
    assert decoded.shape[0] == 400
    assert decoded.shape[1] == 600

    processed = preprocess_pipeline(img_bytes)
    assert processed is not None
    assert isinstance(processed, np.ndarray)


def test_ocr_engine_execution():
    img_bytes = create_synthetic_test_invoice()
    processed = preprocess_pipeline(img_bytes)
    boxes = ocr_engine.run_ocr(processed)

    assert len(boxes) > 0
    extracted_text = " ".join([b.text for b in boxes])
    assert "INVOICE" in extracted_text or "XYZ" in extracted_text or "INV" in extracted_text or "5000" in extracted_text
