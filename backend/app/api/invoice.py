import os
from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from ..config import settings
from ..extraction.fields import FieldExtractor
from ..ocr.engine import ocr_engine
from ..ocr.preprocessing import decode_image, preprocess_pipeline
from ..ocr.quality import quality_checker
from ..schemas.invoice import InvoiceProcessResponse
from ..validation.validator import invoice_validator
from ..vlm.router import vlm_router

router = APIRouter(prefix="/invoice", tags=["Invoice"])


@router.post(
    "/process",
    response_model=InvoiceProcessResponse,
    summary="Process bill/invoice image using Tiered OCR + VLM Fallback Pipeline (stateless)",
)
async def process_invoice(
    file: UploadFile = File(..., description="Bill or invoice image file (JPG, PNG, WebP)"),
    x_api_key: str | None = Header(None, alias="X-API-Key"),
):
    # 1. Optional API Key authentication
    if settings.API_KEY and x_api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key header (X-API-Key)",
        )

    # 2. File extension check
    filename = file.filename or ""
    _, ext = os.path.splitext(filename.lower())
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{ext}'. Allowed: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )

    # 3. Read image bytes into memory & check size
    image_bytes = await file.read()
    if len(image_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )
    if len(image_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image size ({len(image_bytes) / (1024*1024):.1f}MB) exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_BYTES / (1024*1024):.0f}MB.",
        )

    # Determine MIME type
    mime_type = file.content_type or ("image/png" if ext == ".png" else "image/jpeg")

    try:
        # 4. Image Quality Analysis
        raw_img = decode_image(image_bytes)
        quality_report = quality_checker.analyze(raw_img)

        # 5. Local Fast OCR Execution (OpenCV + RapidOCR)
        processed_img = preprocess_pipeline(image_bytes)
        ocr_boxes = ocr_engine.run_ocr(processed_img)

        raw_ocr_text = "\n".join([b.text for b in ocr_boxes])
        extractor = FieldExtractor(ocr_boxes)
        invoice_data, confidence_map = extractor.extract_all()

        # 6. Initial Deterministic Validation
        validation_result = invoice_validator.validate(invoice_data, confidence_map)

        # 7. Evaluate Uncertainty & VLM Fallback Trigger
        conf_values = [v for v in confidence_map.values() if v > 0]
        avg_confidence = sum(conf_values) / len(conf_values) if conf_values else 0.0

        is_uncertain = (
            quality_report.recommend_vlm_direct
            or avg_confidence < settings.VLM_TRIGGER_CONFIDENCE_THRESHOLD
            or not validation_result.valid
            or not invoice_data.total
        )

        extraction_source = "local_rapid_ocr"

        # 8. Trigger VLM Fallback Cascade if uncertain and enabled
        if is_uncertain and settings.ENABLE_VLM_FALLBACK and vlm_router.has_available_providers():
            vlm_data, vlm_conf, provider_name = await vlm_router.extract_invoice(
                image_bytes=image_bytes,
                mime_type=mime_type,
                ocr_text_hint=raw_ocr_text,
            )

            if vlm_data is not None:
                # Re-validate VLM extracted data through deterministic rules
                vlm_validation = invoice_validator.validate(vlm_data, vlm_conf)
                invoice_data = vlm_data
                confidence_map = vlm_conf
                validation_result = vlm_validation
                extraction_source = f"vlm_fallback ({provider_name})"

        # Add image quality warning to validation if relevant
        if quality_report.warning_message and quality_report.warning_message not in validation_result.warnings:
            validation_result.warnings.append(quality_report.warning_message)

        return InvoiceProcessResponse(
            success=True,
            invoice=invoice_data,
            confidence=confidence_map,
            validation=validation_result,
            message=f"Processed via {extraction_source}.",
        )

    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing invoice image: {str(e)}",
        )
    finally:
        del image_bytes
