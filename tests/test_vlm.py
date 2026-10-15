import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.app.vlm.router import VLMRouter
from backend.app.vlm.providers.gemini import GeminiVLMProvider
from backend.app.vlm.providers.groq import GroqVLMProvider
from backend.app.vlm.providers.openrouter import OpenRouterVLMProvider


def test_vlm_router_data_mapping():
    router = VLMRouter()
    raw_dict = {
        "vendor_name": "ABC Logistics",
        "invoice_number": "INV-5501",
        "invoice_date": "2026-09-25",
        "gstin": "08ABCDE1234F1Z5",
        "subtotal": "₹ 10,000.00",
        "cgst": 900,
        "sgst": "900.0",
        "total": "11,800.00",
    }
    inv = router._map_to_invoice_data(raw_dict)

    assert inv.vendor_name == "ABC Logistics"
    assert inv.invoice_number == "INV-5501"
    assert inv.invoice_date == "2026-09-25"
    assert inv.gstin == "08ABCDE1234F1Z5"
    assert inv.subtotal == 10000.00
    assert inv.cgst == 900.00
    assert inv.sgst == 900.00
    assert inv.total == 11800.00


@pytest.mark.anyio
async def test_vlm_router_cascade_failover_on_429():
    router = VLMRouter()

    # Provider 1: Gemini (Raises 429 Quota Exceeded)
    gemini_mock = MagicMock(spec=GeminiVLMProvider)
    gemini_mock.name = "Google Gemini"
    gemini_mock.is_available.return_value = True
    gemini_mock.extract = AsyncMock(side_effect=PermissionError("Gemini API Quota 429"))

    # Provider 2: Groq (Succeeds)
    groq_mock = MagicMock(spec=GroqVLMProvider)
    groq_mock.name = "Groq Vision"
    groq_mock.is_available.return_value = True
    groq_mock.extract = AsyncMock(
        return_value={
            "vendor_name": "Handwritten Chai Shop",
            "invoice_number": "CHAI-001",
            "invoice_date": "2026-09-25",
            "total": 550.0,
        }
    )

    # Provider 3: OpenRouter
    openrouter_mock = MagicMock(spec=OpenRouterVLMProvider)
    openrouter_mock.name = "OpenRouter"
    openrouter_mock.is_available.return_value = True

    router.providers = [gemini_mock, groq_mock, openrouter_mock]

    inv_data, conf, provider_used = await router.extract_invoice(b"dummy_image")

    assert inv_data is not None
    assert inv_data.vendor_name == "Handwritten Chai Shop"
    assert inv_data.total == 550.0
    assert provider_used == "Groq Vision"
    gemini_mock.extract.assert_awaited_once()
    groq_mock.extract.assert_awaited_once()


@pytest.mark.anyio
async def test_vlm_router_no_keys_configured():
    router = VLMRouter()
    for p in router.providers:
        p.api_keys = []

    assert router.has_available_providers() is False
    inv, conf, provider = await router.extract_invoice(b"dummy")
    assert inv is None
    assert provider is None
