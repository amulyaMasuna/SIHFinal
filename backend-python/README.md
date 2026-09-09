# LegalLens - Python AI Microservice for Legal Metrology Rules 2011 Compliance

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.8+-5C3EE8.svg?style=flat&logo=opencv)](https://opencv.org)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-v2.8-red.svg?style=flat)](https://github.com/PaddlePaddle/PaddleOCR)
[![Legal Metrology](https://img.shields.io/badge/Regulation-LMR%202011%20India-blue.svg)](https://consumeraffairs.nic.in)

Autonomous AI Microservice designed to perform optical label inspection and statutory compliance auditing under the **Legal Metrology (Packaged Commodities) Rules, 2011 (India)** and the **Legal Metrology Act, 2009**.

Integrates seamlessly with the **Node.js Express Gateway** (`backend-node`) and the **React PWA Frontend** (`frontend-react`).

---

## Architecture & Pipeline

```
[ Packaging Label Image ]
           │
           ▼
┌────────────────────────────────────────────────────────┐
│ 1. OpenCV Preprocessing Pipeline                       │
│    - Aspect-ratio preserving dynamic rescaling         │
│    - EXIF auto-orientation                            │
│    - CLAHE (Contrast Limited Adaptive Hist. Eq.)       │
│    - Bilateral edge-preserving noise filter            │
│    - Skew detection & auto-rotation (minAreaRect)      │
│    - Adaptive Gaussian & Otsu binarization             │
└──────────────────────────┬─────────────────────────────┘
                           │ Enhanced BGR ndarray
                           ▼
┌────────────────────────────────────────────────────────┐
│ 2. PaddleOCR Deep Learning Text Extraction             │
│    - Angle classification (use_angle_cls=True)         │
│    - Spatial reading order sorting (Y-band & X-sort)   │
│    - Bounding box coordinates & confidence scores      │
└──────────────────────────┬─────────────────────────────┘
                           │ Raw text lines & boxes
                           ▼
┌────────────────────────────────────────────────────────┐
│ 3. Regex & NLP Semantic Entity Parser                  │
│    - Maximum Retail Price (MRP) & Tax Syntax           │
│    - Unit Sale Price (USP) (2022 Amendment)            │
│    - Net Quantity & Unit symbols (g, kg, ml, l, N)     │
│    - Prohibited units check (gms, gm, kilo, ltr, ml.)  │
│    - Prohibited qualifying words (approx, when packed) │
│    - Manufacturing, Packaging, & Expiry Dates          │
│    - Manufacturer / Packer / Importer postal address   │
│    - Consumer Care grievance contacts (Email & Phone)  │
│    - Country of Origin & Generic Commodity Name        │
└──────────────────────────┬─────────────────────────────┘
                           │ Structured Entity JSON
                           ▼
┌────────────────────────────────────────────────────────┐
│ 4. Statutory Legal Metrology Validation Engine         │
│    - Rule 6(1)(a): Complete Manufacturer Postal Address│
│    - Rule 6(1)(b): Generic Commodity Name              │
│    - Rule 6(1)(c) & Rule 13: Net Qty in SI Units       │
│    - Rule 6(1)(d): Month & Year of Mfg/Packing         │
│    - Rule 6(1)(e): MRP inclusive of all taxes          │
│    - Rule 6(1)(f): Consumer Care Email & Telephone     │
│    - Rule 6(10): Mandatory Country of Origin          │
│    - Rule 6(11): Mandatory Unit Sale Price (> 1kg/1L) │
│    - Rule 11: Prohibition of qualifying words          │
│    - Section 36 Show-Cause Inspection Notice Generator │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
[ Standardized JSON Response to Node Gateway / React ]
```

---

## Statutory Rules Audited

| Statutory Rule | Description | Severity | Mandate |
|---|---|---|---|
| **Rule 6(1)(a)** | Manufacturer / Packer / Importer Identity | `CRITICAL` / `MAJOR` | Complete name & postal address with PIN code |
| **Rule 6(1)(b)** | Generic Commodity Name | `MAJOR` | Prominent common or generic product name |
| **Rule 6(1)(c)** | Net Quantity Declaration | `CRITICAL` | Nominal net quantity in standard units |
| **Rule 13** | Standard Units of Measurement | `MAJOR` | Standard SI symbols (`g`, `kg`, `ml`, `l`, `N`). Prohibits `gms`, `gm`, `kilo`, `ltr`, `ml.` |
| **Rule 11** | Qualifying Words Prohibition | `MAJOR` | Strictly forbids words like "approximate" or "when packed" |
| **Rule 6(1)(d)** | Month & Year of Mfg/Packing | `MAJOR` | Conspicuous MM/YYYY or Month YYYY format |
| **Rule 6(1)(e)** | Maximum Retail Price (MRP) | `CRITICAL` | Must state "inclusive of all taxes". "Taxes extra" is illegal |
| **Rule 6(1)(f)** | Consumer Care Grievance Redressal | `CRITICAL` | Complete telephone number and email address |
| **Rule 6(10)** | Mandatory Country of Origin | `MAJOR` | Prominently state "Country of Origin: India" or country of import |
| **Rule 6(11)** | Unit Sale Price (USP) | `MAJOR` | Mandatory declaration per g/kg/ml/l for packs > 1 kg or 1 L |
| **Section 36** | Penalty & Legal Notice Generation | `LEGAL ENFORCEMENT` | Automated draft notice under Legal Metrology Act, 2009 |

---

## API Endpoints

### 1. Optical Inspection & Compliance Audit
- **Endpoint**: `POST /api/v1/extract`
- **Content-Type**: `multipart/form-data`
- **Parameters**:
  - `file`: (Required) Packaging label image (JPEG, PNG, WEBP)
  - `include_preview`: (Optional, default `false`) Returns enhanced image as base64 data URI

**Sample Request (`curl`)**:
```bash
curl -X POST "http://localhost:8000/api/v1/extract" \
  -F "file=@packaging_label.jpg"
```

**Response Format**:
```json
{
  "success": true,
  "filename": "packaging_label.jpg",
  "ocr_engine_used": "PaddleOCR (Deep Learning Engine with Angle Classifier)",
  "raw_text_lines": [
    "PREMIUM ASSAM TEA",
    "MRP Rs. 249.00 (inclusive of all taxes)",
    "Net Qty: 500 g",
    "Mfg Date: 03/2026",
    "Manufactured by: Tata Consumer Products Ltd, Pune Industrial Area, Pune 411001",
    "Consumer Care Cell: Email: care@tataconsumer.com, Tel: 1800-108-4488",
    "Country of Origin: India"
  ],
  "parsed_entities": {
    "mrp_raw": "MRP Rs. 249.00 (inclusive of all taxes)",
    "mrp_value": 249.0,
    "currency": "Rs.",
    "tax_inclusive": true,
    "tax_extra_detected": false,
    "net_qty_raw": "Net Qty: 500 g",
    "net_qty_value": 500.0,
    "net_qty_unit": "g",
    "is_non_standard_unit": false,
    "mfg_date_raw": "Mfg Date: 03/2026",
    "consumer_care_email": "care@tataconsumer.com",
    "consumer_care_phone": "1800-108-4488",
    "manufacturer_details": "Manufactured by: Tata Consumer Products Ltd, Pune Industrial Area, Pune 411001",
    "country_of_origin": "India"
  },
  "bounding_boxes": [
    {
      "box": [[50, 40], [350, 40], [350, 70], [50, 70]],
      "text": "MRP Rs. 249.00 (inclusive of all taxes)",
      "confidence": 0.98
    }
  ],
  "compliance_audit": {
    "status": "PASS",
    "total_violations": 0,
    "compliance_score": 100,
    "violations": [],
    "flags": [],
    "legal_notice_draft": "COMPLIANT: No statutory violation detected..."
  },
  "preprocessing_metadata": {
    "original_dims": { "width": 1920, "height": 1080 },
    "processed_dims": { "width": 1800, "height": 1012 },
    "scale_factor": 0.937,
    "skew_angle": 0.0,
    "clahe_applied": true,
    "denoising_applied": true
  },
  "processing_time_ms": 142.5
}
```

### 2. Direct Text / Entity Validation
- **Endpoint**: `POST /api/v1/validate`
- **Content-Type**: `application/json`
- **Payload**:
```json
{
  "text": "MRP Rs. 150 Taxes Extra\nNet Wt: 250 gms"
}
```

### 3. Statutory Rules Directory
- **Endpoint**: `GET /api/v1/rules`
- Returns full reference catalog of all statutory rules, titles, and legal penalty sections.

### 4. Health Checks
- `GET /` - Service status, regulations, and active OCR engine metadata
- `GET /healthz` - Lightweight 200 OK healthcheck for container orchestration

---

## Local Setup & Installation

### Prerequisites
- Python 3.10+ (Recommended for PaddleOCR)
- System C++ libraries (for OpenCV and Paddle)

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python test_service.py
```

### 3. Start Development Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI documentation is available at:
`http://localhost:8000/docs`

---

## Docker Deployment

Build and run using the optimized Docker container:

```bash
docker build -t legal-metrology-ai .
docker run -p 8000:8000 legal-metrology-ai
```

---

## Render Deployment (`render.yaml`)

This microservice is preconfigured in `SIHFinal/render.yaml`:

```yaml
services:
  - type: web
    name: legal-metrology-ai-python
    env: python
    rootDir: backend-python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    plan: free
    region: oregon
    healthCheckPath: /
    envVars:
      - key: PYTHON_VERSION
        value: 3.10.12
```
