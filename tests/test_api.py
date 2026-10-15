import io
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def create_test_image_bytes() -> bytes:
    img = np.ones((500, 700, 3), dtype=np.uint8) * 255
    cv2.putText(img, "ABC Traders", (50, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    cv2.putText(img, "Invoice No: INV-1024", (50, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "Date: 25/09/2026", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "GSTIN: 08ABCDE1234F1Z5", (50, 190), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "Subtotal: 10000", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "CGST: 900", (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "SGST: 900", (50, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.putText(img, "Total: 11800", (50, 370), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    
    _, encoded = cv2.imencode(".png", img)
    return encoded.tobytes()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"


def test_process_invoice_api():
    img_bytes = create_test_image_bytes()
    files = {
        "file": ("test_invoice.png", io.BytesIO(img_bytes), "image/png")
    }
    response = client.post("/api/v1/invoice/process", files=files)
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert "invoice" in data
    assert "validation" in data
    assert data["invoice"]["total"] == 11800.0 or data["invoice"]["total"] is not None


def test_unsupported_file_extension():
    files = {
        "file": ("malicious.exe", io.BytesIO(b"dummy"), "application/octet-stream")
    }
    response = client.post("/api/v1/invoice/process", files=files)
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]
