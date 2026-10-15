# Bill Image to ERP Automation System
### Tiered Local OCR + Remote VLM Failover Cascade (Stateless & Human-in-the-Loop)

An enterprise-grade, privacy-first automation pipeline designed to extract bill and invoice data from scanned documents, mobile snapshots, and messy receipts, and autofill them directly into web-based ERP systems (SAP, Oracle, Odoo, QuickBooks, custom web forms).

Combines ultra-fast local CPU inference (**RapidOCR / PP-OCR**) with a multi-provider fallback cascade (**Google Gemini $\rightarrow$ Groq Vision $\rightarrow$ OpenRouter**) and a modern **Manifest V3 browser extension**.

---

## 📑 Table of Contents
1. [Core Philosophy & Architecture](#-core-philosophy--architecture)
2. [Every Problem Encountered & Engineered Solution](#-every-problem-encountered--engineered-solution)
   - [Business & Compliance Problems](#1-business--compliance-problems)
   - [Computer Vision & OCR Problems](#2-computer-vision--ocr-problems)
   - [AI & Rate-Limiting Problems](#3-ai--rate-limiting-problems)
   - [Browser & ERP Integration Problems](#4-browser--erp-integration-problems)
   - [Runtime, Memory & Hosting Problems](#5-runtime-memory--hosting-problems)
3. [System Workflow Diagram](#-system-workflow-diagram)
4. [Project Structure](#-project-structure)
5. [Configuration & Environment Variables](#-configuration--environment-variables)
6. [How to Run Locally](#-how-to-run-locally)
7. [Automated Testing](#-automated-testing)
8. [Deployment & Free Hosting Guide](#-deployment--free-hosting-guide)

---

## 🏗 Core Philosophy & Architecture

1. **Stateless by Design**: No database (no PostgreSQL, MongoDB, or SQLite). Images are processed in-memory (RAM buffer) during the HTTP request lifecycle and discarded immediately. No financial data is retained.
2. **Human-in-the-Loop (Zero Blind Automation)**: The system extracts, validates, and populates ERP form fields, but **never clicks the final ERP Submit button**. The accountant or user verifies the data and clicks Submit.
3. **Tiered Cost Optimization**: Runs 100% free on local CPU using RapidOCR for clean documents ($0 cost). Remote VLMs are only engaged when local confidence is low or images are degraded.

---

## 🥊 Every Problem Encountered & Engineered Solution

### 1. Business & Compliance Problems

#### Problem 1.1: The Manual ERP Data Entry Bottleneck
* **The Problem**: Accountants spend 3–7 minutes manually keying in vendor names, invoice numbers, GSTIN/Tax IDs, dates, line items, and totals into ERP forms. Typos lead to incorrect tax filings and reconciliation disputes.
* **Engineered Solution**: Automatic image analysis extracts structured data in < 800ms. A browser extension autofills all matching ERP fields with visual glow indicators (`box-shadow: 0 0 8px #22c55e`).

#### Problem 1.2: The "Blind Automation" Accounting Liability
* **The Problem**: Fully autonomous bots that submit invoices directly into general ledgers risk creating duplicate payments, posting hallucinated tax amounts, or violating audit standards.
* **Engineered Solution**: Strict **Human-in-the-Loop verification**. The Chrome/Edge extension presents an editable review panel showing confidence scores and validation badges. The accountant reviews the values, clicks **"Fill ERP Fields"**, visually checks the form on the page, and manually clicks the ERP **Submit** button.

#### Problem 1.3: Data Privacy & Compliance (GDPR, SOC2, HIPAA)
* **The Problem**: Storing invoice images and vendor payment details in a cloud database creates severe data breach liability and compliance overhead.
* **Engineered Solution**: **Zero Data Retention (Stateless)**. The backend uses Python in-memory byte buffers (`io.BytesIO`). No files are saved to disk, no databases exist, and memory buffers are cleared by the garbage collector immediately after the response is sent.

---

### 2. Computer Vision & OCR Problems

#### Problem 2.1: Phone Photos, Blurry Scans & Shadows
* **The Problem**: Real-world bills are often photographed with mobile cameras under bad lighting, angled desks, or camera shake. Standard OCR engines hallucinate or fail completely on un-preprocessed photos.
* **Engineered Solution**: An automated OpenCV quality check pipeline evaluates:
  - **Blur Detection**: Laplacian variance ($\sigma^2 < 80.0$ flags the image as blurry).
  - **Contrast & Illumination**: RMS contrast and mean brightness checking.
  - **Adaptive Preprocessing**: Grayscale conversion, Otsu binarization, and morphological filtering before OCR.

#### Problem 2.2: Character Confusion (0 vs O, 1 vs I, 5 vs S) & Tax ID Validation
* **The Problem**: OCR frequently misreads `0` for `O` or `1` for `I` in structured fields like India GSTIN (`08ABCDE1234F1Z5`) or invoice numbers.
* **Engineered Solution**: Regex-based post-processing and syntactic checksum verification. The system checks standard tax ID schemas (e.g. 15-character alphanumeric GSTIN formats) and normalizes messy dates (`DD/MM/YYYY`, `MM-DD-YYYY`, `YYYY.MM.DD`) into ISO-8601 standard format.

#### Problem 2.3: Mathematical Inconsistencies & Misread Line Items
* **The Problem**: OCR might accurately read the subtotal and tax, but misread the total amount (e.g. reading `$1000` as `$100` or `$1080` instead of `$1180`).
* **Engineered Solution**: **Deterministic Pydantic Validation Guardrail**. The backend checks:
  $$\text{Subtotal} + \text{Tax} \approx \text{Total} \quad (\pm 1.00 \text{ tolerance for rounding})$$
  If the equation fails or confidence is below $75\%$, the backend flags `requires_human_review = True` and triggers Tier 2 VLM fallback.

---

### 3. AI & Rate-Limiting Problems

#### Problem 3.1: Cloud VLMs (GPT-4o / Claude) are Expensive & Slow
* **The Problem**: Calling frontier vision models for every single invoice costs money and adds 2–4 seconds of network latency.
* **Engineered Solution**: **Tiered Hybrid Architecture**:
  - **Tier 1 (Local CPU RapidOCR)**: Runs locally in ~250ms at **$0 cost**. Handles clean scans and standard digital invoices.
  - **Tier 2 (Remote VLM)**: Only called if Tier 1 confidence $< 75\%$, blur $> 80$, or math validation fails.

#### Problem 3.2: Free Tier API Rate Limits (HTTP 429 Quota Exceeded)
* **The Problem**: Free tier AI providers (Google AI Studio, Groq, OpenRouter) enforce strict rate limits (e.g., 15 requests/minute). When traffic spikes, 429 errors crash single-provider systems.
* **Engineered Solution**: **Multi-Provider Fallback Cascade**:
  $$\text{Google Gemini Flash} \xrightarrow{\text{429 or Error}} \text{Groq Vision (Llama 3.2)} \xrightarrow{\text{429 or Error}} \text{OpenRouter Free Tier}$$
  If all remote providers fail or no API keys are provided in `.env`, the system gracefully falls back to local RapidOCR without crashing.

---

### 4. Browser & ERP Integration Problems

#### Problem 4.1: React / Vue / Angular Ignoring Injected Values
* **The Problem**: When a browser extension sets an input field using `input.value = "123"`, modern frontend frameworks (React, Vue, Angular) do not detect the change because their internal virtual DOM state is not updated. When the user clicks submit, the fields revert to blank!
* **Engineered Solution**: Native Prototype Setter Injection. The content script overrides the input value using:
  ```javascript
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, 'value'
  ).set;
  nativeInputValueSetter.call(inputElement, value);
  inputElement.dispatchEvent(new Event('input', { bubbles: true }));
  inputElement.dispatchEvent(new Event('change', { bubbles: true }));
  ```

#### Problem 4.2: ERP Forms Have Inconsistent Field Selectors
* **The Problem**: Different ERPs (Odoo, SAP, custom internal portals) name their fields differently (`inv_total`, `grandTotal`, `amount_due`, `bill_no`).
* **Engineered Solution**: Fuzzy heuristic attribute matching. The extension script scans:
  1. Exact ID and name matches
  2. Substring matching across `id`, `name`, `placeholder`, and `aria-label`
  3. Associated `<label>` text content

---

### 5. Runtime, Memory & Hosting Problems

#### Problem 5.1: `ImportError: attempted relative import with no known parent package`
* **The Problem**: Running `python backend/app/main.py` directly throws this error because FastAPI is an ASGI module that relies on package-relative imports (`from .api.invoice import router`).
* **Engineered Solution**: Use the dedicated root runner **`run.py`** or launch with Uvicorn:
  ```powershell
  python run.py
  # OR
  uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
  ```

#### Problem 5.2: Memory Footprint (400–500 MB) vs 512 MB Free Hosting Tiers
* **The Problem**: RapidOCR runs ONNX models (detection, classification, recognition) on CPU. Loading these models alongside OpenCV and NumPy requires ~350 MB – 450 MB RAM. On platforms with a strict 512 MB RAM ceiling (like Render.com free tier), a large image upload can cause an Out-Of-Memory (OOM) process kill.
* **Engineered Solutions**:
  - **Solution A (Recommended for Free Hosting)**: Deploy to **Hugging Face Spaces (Docker)**, which provides **16 GB RAM for free** (no credit card).
  - **Solution B (Ultra-Low Memory Mode)**: If deploying to a 512 MB host like Render, you can disable local RapidOCR and rely 100% on Groq Cloud VLM. RAM usage drops to **< 70 MB**, and Docker image size drops from 600 MB to 160 MB.

#### Problem 5.3: Missing Linux System Libraries for OpenCV/ONNX in Docker
* **The Problem**: `opencv-python` and `onnxruntime` crash inside slim Linux containers (`python:3.10-slim`) with: `ImportError: libGL.so.1: cannot open shared object file`.
* **Engineered Solution**: The multi-stage [`backend/Dockerfile`](file:///c:/Machine%20Learning/ocr-workflow/backend/Dockerfile) installs the required runtime libraries:
  ```dockerfile
  RUN apt-get update && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libgomp1 \
      && rm -rf /var/lib/apt/lists/*
  ```

---

## 🔄 System Workflow Diagram

```text
                     Bill Image (JPG / PNG / WebP)
                                  │
                                  ▼
                     ┌──────────────────────────┐
                     │  OpenCV Quality Checker  │  ◄── Laplacian Blur / Contrast Check
                     └────────────┬─────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         │ (Sharp / High Contrast)                         │ (Blurry / Low Lighting)
         ▼                                                 │
┌─────────────────────────┐                                │
│ RapidOCR (ONNX Local)   │ ($0 CPU Inference)             │
└────────┬────────────────┘                                │
         ▼                                                 │
┌─────────────────────────┐                                │
│ Rule & Regex Extraction │                                │
└────────┬────────────────┘                                │
         ▼                                                 │
  [Math Check & Confidence]                                │
   ├─► Reliable (>= 75% & Math OK) ──────────────┐         │
   │                                             │         │
   └─► Uncertain (< 75% or Math Mismatch) ───────┼─────────┘
                                                 │
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │   Remote VLM Fallback Chain   │
                                 │   1. Google Gemini 1.5 Flash  │
                                 │      ↓ (On 429 Quota Exceed)  │
                                 │   2. Groq Vision (Llama 3.2)  │
                                 │      ↓ (On 429 Quota Exceed)  │
                                 │   3. OpenRouter Free Tier     │
                                 └───────────────┬───────────────┘
                                                 │
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │ Deterministic Validation Gate │ ◄── Subtotal + Tax == Total
                                 │ (Pydantic / Clean Normalizer) │
                                 └───────────────┬───────────────┘
                                                 │
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │ Browser Extension (Review UI) │ ◄── Human Verification
                                 └───────────────┬───────────────┘
                                                 │ (User clicks "Fill ERP Fields")
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │ ERP Form Populated & Glowing  │ ◄── React/Vue Event Dispatch
                                 └───────────────┬───────────────┘
                                                 │
                                                 ▼
                                 ┌───────────────────────────────┐
                                 │ Human Clicks Final ERP Submit │
                                 └───────────────────────────────┘
```

---

## 📁 Project Structure

```text
ocr-workflow/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── invoice.py        # Main stateless /process endpoint
│   │   ├── extraction/
│   │   │   ├── fields.py         # Regex, spatial mapping, and normalization
│   │   │   └── patterns.py       # GSTIN, Date, Total, and Invoice patterns
│   │   ├── ocr/
│   │   │   ├── engine.py         # RapidOCR (ONNX Runtime) singleton
│   │   │   ├── preprocessing.py  # OpenCV thresholding, deskew, and cleanup
│   │   │   └── quality.py        # Laplacian blur, brightness, contrast detection
│   │   ├── schemas/
│   │   │   └── invoice.py        # Pydantic data contracts and schemas
│   │   ├── validation/
│   │   │   └── validator.py      # Math consistency & confidence guardrails
│   │   ├── vlm/
│   │   │   ├── cascade.py        # Fallback executor (Gemini -> Groq -> OpenRouter)
│   │   │   ├── gemini.py         # Google Gemini Flash client
│   │   │   ├── groq.py           # Groq Vision (Llama 3.2) client
│   │   │   ├── openrouter.py     # OpenRouter Free Tier client
│   │   │   └── router.py         # VLM routing layer
│   │   ├── config.py             # Settings and environment variables
│   │   └── main.py               # FastAPI application factory
│   ├── Dockerfile                # Production container specification
│   └── requirements.txt          # Production Python dependencies
├── extension/                    # Manifest V3 Chrome / Edge Extension
│   ├── manifest.json             # Extension permissions and config
│   ├── popup.html / popup.js     # Side-panel UI for image upload & review
│   └── content.js                # DOM injection script with React event support
├── mock_erp/
│   └── index.html                # Local interactive ERP testing form
├── tests/                        # Automated Pytest test suite (21 unit tests)
├── .env.example                  # Template for API keys
├── docker-compose.yml            # Multi-container local orchestration
├── generate_sample_invoice.py    # Generates a synthetic test invoice image
└── run.py                        # Root runner script for local development
```

---

## 🔑 Configuration & Environment Variables

Copy `.env.example` to `.env` in the project root:

```bash
# Optional API Authentication (Header: X-API-Key)
API_KEY=

# Remote VLM Provider API Keys (All have generous free tiers)
GEMINI_API_KEY=your_gemini_api_key       # https://aistudio.google.com/
GROQ_API_KEY=your_groq_api_key           # https://console.groq.com/
OPENROUTER_API_KEY=your_openrouter_key   # https://openrouter.ai/keys

# Pipeline Thresholds
ENABLE_VLM_FALLBACK=true
VLM_TRIGGER_CONFIDENCE_THRESHOLD=0.75
BLUR_THRESHOLD=80.0
```

> **Note:** If no API keys are provided, the backend operates 100% locally on CPU using RapidOCR without making any external network requests.

---

## 🚀 How to Run Locally

### 1. Start the Backend Server

Using the runner file:
```powershell
python run.py
```
Or directly using Uvicorn:
```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

* **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **Health Check Endpoint**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Load the Browser Extension
1. Open Google Chrome or Microsoft Edge and navigate to `chrome://extensions/`
2. Toggle on **Developer Mode** (top right corner).
3. Click **Load unpacked** and select the `extension/` folder from this repo.

### 3. Test End-to-End with Mock ERP
1. Open [`mock_erp/index.html`](file:///c:/Machine%20Learning/ocr-workflow/mock_erp/index.html) in your browser.
2. Click the extension icon in your browser toolbar.
3. Drop [`sample_invoice.png`](file:///c:/Machine%20Learning/ocr-workflow/sample_invoice.png) into the extension popup.
4. Review the extracted fields and confidence badges.
5. Click **"Fill ERP Fields"** — observe the mock ERP form populate and glow green.
6. Manually click the ERP **"Save / Submit Bill"** button.

---

## 🧪 Automated Testing

The project includes 21 comprehensive unit and integration tests covering image quality assessment, OCR preprocessing, regex extraction, deterministic validation, and the VLM failover cascade:

```powershell
pytest -v
```

---

## ☁️ Deployment & Free Hosting Guide

### Option 1: Hugging Face Spaces (Recommended — 100% Free)
* **Why**: Provides **16 GB RAM** and 2 vCPUs for free (no credit card required). RapidOCR and ONNX run smoothly with zero OOM risk.
* **Steps**:
  1. Go to [huggingface.co](https://huggingface.co) and create a **New Space**.
  2. Select **Docker** as the Space SDK and set it to **Blank**.
  3. Push your repository to the Space.
  4. Ensure port `7860` is exposed in `backend/Dockerfile`.
  5. Your API is live at `https://<username>-<space-name>.hf.space`.

### Option 2: Render.com (Docker Web Service)
* **Specs**: 512 MB RAM, free tier.
* **Steps**:
  1. Connect your GitHub repository to [render.com](https://render.com).
  2. Create a new **Web Service**, set Runtime to **Docker**, Docker Context to `.`, and Dockerfile to `backend/Dockerfile`.
  3. Add your `GROQ_API_KEY` and `GEMINI_API_KEY` under Environment Variables.
  4. *Tip*: If you notice memory warnings, switch to pure Cloud VLM mode to reduce RAM usage from 450 MB to 70 MB.
