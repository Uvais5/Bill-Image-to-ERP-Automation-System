import logging
from typing import Dict, List, Optional, Tuple
from ..schemas.invoice import InvoiceData
from .providers.gemini import GeminiVLMProvider
from .providers.groq import GroqVLMProvider
from .providers.openrouter import OpenRouterVLMProvider

logger = logging.getLogger(__name__)


class VLMRouter:
    def __init__(self):
        self.providers = [
            GeminiVLMProvider(),
            GroqVLMProvider(),
            OpenRouterVLMProvider(),
        ]

    def has_available_providers(self) -> bool:
        return any(p.is_available() for p in self.providers)

    async def extract_invoice(
        self,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        ocr_text_hint: str = "",
    ) -> Tuple[Optional[InvoiceData], Dict[str, float], Optional[str]]:
        """
        Attempts invoice extraction across configured VLM providers in cascade order:
        Gemini -> Groq -> OpenRouter.
        Returns: (InvoiceData, confidence_map, provider_name)
        """
        available_providers = [p for p in self.providers if p.is_available()]
        if not available_providers:
            logger.warning("No remote VLM providers are configured with API keys.")
            return None, {}, None

        last_error = None
        for provider in available_providers:
            try:
                logger.info(f"Attempting VLM extraction using: {provider.name}")
                raw_dict = await provider.extract(
                    image_bytes=image_bytes,
                    mime_type=mime_type,
                    ocr_text=ocr_text_hint,
                )

                # Parse into InvoiceData
                invoice_data = self._map_to_invoice_data(raw_dict)
                confidence_map = self._build_vlm_confidence_map(invoice_data)

                logger.info(f"Successfully extracted invoice via {provider.name}")
                return invoice_data, confidence_map, provider.name

            except PermissionError as qe:
                logger.warning(f"{provider.name} rate limit / quota exceeded (429). Cascading to next provider: {qe}")
                last_error = qe
            except Exception as e:
                logger.warning(f"Error with {provider.name}: {e}. Cascading to next provider.")
                last_error = e

        logger.error(f"All available VLM providers failed. Last error: {last_error}")
        return None, {}, None

    def _map_to_invoice_data(self, d: Dict) -> InvoiceData:
        def clean_float(val):
            if val is None:
                return None
            try:
                if isinstance(val, (int, float)):
                    return float(val)
                val_str = str(val).replace("₹", "").replace("Rs.", "").replace("Rs", "").replace(",", "").strip()
                return float(val_str)
            except (ValueError, TypeError):
                return None

        return InvoiceData(
            vendor_name=str(d.get("vendor_name")).strip() if d.get("vendor_name") else None,
            item_name=str(d.get("item_name")).strip() if d.get("item_name") else None,
            invoice_number=str(d.get("invoice_number")).strip() if d.get("invoice_number") else None,
            invoice_date=str(d.get("invoice_date")).strip() if d.get("invoice_date") else None,
            gstin=str(d.get("gstin")).strip().upper() if d.get("gstin") else None,
            subtotal=clean_float(d.get("subtotal")),
            cgst=clean_float(d.get("cgst")),
            sgst=clean_float(d.get("sgst")),
            igst=clean_float(d.get("igst")),
            total=clean_float(d.get("total")),
            description=str(d.get("description")).strip() if d.get("description") else None,
        )

    def _build_vlm_confidence_map(self, inv: InvoiceData) -> Dict[str, float]:
        conf = {}
        for field in ["vendor_name", "item_name", "invoice_number", "invoice_date", "gstin", "subtotal", "cgst", "sgst", "igst", "total", "description"]:
            val = getattr(inv, field, None)
            conf[field] = 0.95 if val is not None else 0.0
        return conf


vlm_router = VLMRouter()
