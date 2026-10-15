import os
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    PROJECT_NAME: str = "Bill Image to ERP Backend"
    VERSION: str = "1.1.0"
    API_V1_STR: str = "/api/v1"

    # Security / Auth
    API_KEY: Optional[str] = os.getenv("API_KEY", None)

    # Remote VLM Provider API Keys
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    GROQ_API_KEY: Optional[str] = os.getenv("GROQ_API_KEY", None)
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY", None)

    # VLM Models
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.2-11b-vision-preview")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")

    # VLM Triggering & Quality settings
    ENABLE_VLM_FALLBACK: bool = os.getenv("ENABLE_VLM_FALLBACK", "true").lower() in ("true", "1", "yes")
    VLM_TRIGGER_CONFIDENCE_THRESHOLD: float = float(os.getenv("VLM_TRIGGER_CONFIDENCE_THRESHOLD", "0.75"))
    BLUR_THRESHOLD: float = float(os.getenv("BLUR_THRESHOLD", "80.0"))

    # CORS
    CORS_ORIGINS: List[str] = [
        "chrome-extension://*",
        "moz-extension://*",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:5500",
    ]

    # Upload limits
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".webp"}
    ALLOWED_MIME_TYPES: set = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "application/octet-stream",
    }

    # OCR & Validation settings
    OCR_CONFIDENCE_THRESHOLD_HIGH: float = 0.85
    OCR_CONFIDENCE_THRESHOLD_MEDIUM: float = 0.60
    AMOUNT_TOLERANCE: float = 1.00  # Rs 1 tolerance for rounding differences


settings = Settings()
