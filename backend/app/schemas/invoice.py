from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class InvoiceData(BaseModel):
    vendor_name: Optional[str] = None
    item_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    gstin: Optional[str] = None
    subtotal: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total: Optional[float] = None
    description: Optional[str] = None


class ValidationResult(BaseModel):
    valid: bool
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


class OCRBox(BaseModel):
    text: str
    confidence: float
    bbox: List[int]  # [x_min, y_min, x_max, y_max]


class InvoiceProcessResponse(BaseModel):
    success: bool
    invoice: InvoiceData
    confidence: Dict[str, float] = Field(default_factory=dict)
    validation: ValidationResult
    message: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    version: str
