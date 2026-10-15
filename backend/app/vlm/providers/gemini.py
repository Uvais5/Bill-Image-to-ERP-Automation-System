import base64
import json
import logging
from typing import Dict, List, Optional
import httpx
from ...config import settings
from ..prompt import SYSTEM_INVOICE_PROMPT, format_user_prompt

logger = logging.getLogger(__name__)

FALLBACK_MODELS = [
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-flash-latest",
]


class GeminiVLMProvider:
    def __init__(self, api_keys_str: Optional[str] = None, model: Optional[str] = None):
        raw_keys = api_keys_str or settings.GEMINI_API_KEY or ""
        self.api_keys: List[str] = [k.strip() for k in raw_keys.split(",") if k.strip()]
        self.model = model or settings.GEMINI_MODEL
        self.name = "Google Gemini"
        self._current_key_idx = 0

    def is_available(self) -> bool:
        return len(self.api_keys) > 0

    async def extract(self, image_bytes: bytes, mime_type: str = "image/jpeg", ocr_text: str = "") -> Dict:
        if not self.is_available():
            raise ValueError("No Gemini API keys are configured.")

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        models_to_try = [self.model] + [m for m in FALLBACK_MODELS if m != self.model]

        last_error = None
        # Try every configured API key in rotation
        for attempt in range(len(self.api_keys)):
            current_key = self.api_keys[self._current_key_idx]
            headers = {
                "x-goog-api-key": current_key,
                "Content-Type": "application/json",
            }

            payload = {
                "system_instruction": {
                    "parts": [{"text": SYSTEM_INVOICE_PROMPT}]
                },
                "contents": [
                    {
                        "parts": [
                            {
                                "text": format_user_prompt(ocr_text)
                            },
                            {
                                "inline_data": {
                                    "mime_type": mime_type,
                                    "data": b64_image,
                                }
                            },
                        ]
                    }
                ],
                "generationConfig": {
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            }

            # Try models for the current key
            for model_name in models_to_try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
                try:
                    async with httpx.AsyncClient(timeout=25.0) as client:
                        response = await client.post(url, headers=headers, json=payload)

                        if response.status_code == 200:
                            result = response.json()
                            candidates = result.get("candidates", [])
                            if candidates:
                                content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                return self._parse_json(content_text)

                        if response.status_code == 429:
                            logger.warning(
                                f"Gemini Key #{self._current_key_idx + 1} quota exceeded (429). Rotating to next key..."
                            )
                            break  # Break model loop to rotate key

                        if response.status_code in (503, 404):
                            logger.info(f"Gemini {model_name} returned {response.status_code}, trying fallback model...")
                            continue  # Try next model

                        last_error = f"Gemini API Error ({response.status_code}): {response.text}"

                except Exception as e:
                    last_error = str(e)
                    continue

            # Advance to next key for next request/retry
            self._current_key_idx = (self._current_key_idx + 1) % len(self.api_keys)

        raise RuntimeError(f"All Gemini API keys failed. Last error: {last_error}")

    def _parse_json(self, raw_text: str) -> Dict:
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
