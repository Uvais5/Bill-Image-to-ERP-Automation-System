import base64
import json
from typing import Dict, Optional
import httpx
from ...config import settings
from ..prompt import SYSTEM_INVOICE_PROMPT, format_user_prompt


class OpenRouterVLMProvider:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.name = "OpenRouter Free VLM"

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.strip())

    async def extract(self, image_bytes: bytes, mime_type: str = "image/jpeg", ocr_text: str = "") -> Dict:
        if not self.is_available():
            raise ValueError("OpenRouter API key is not configured.")

        b64_image = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_image}"

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Invoice ERP Assistant",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_INVOICE_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": format_user_prompt(ocr_text)},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_uri},
                        },
                    ],
                },
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(url, headers=headers, json=payload)

            if response.status_code == 429:
                raise PermissionError(f"OpenRouter API Quota / Rate Limit Exceeded (429): {response.text}")
            if response.status_code != 200:
                raise RuntimeError(f"OpenRouter API Error ({response.status_code}): {response.text}")

            result = response.json()
            raw_content = result["choices"][0]["message"]["content"]
            return self._parse_json(raw_content)

    def _parse_json(self, raw_text: str) -> Dict:
        cleaned = raw_text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return json.loads(cleaned.strip())
