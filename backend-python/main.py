"""
LegalLens - Python AI Microservice for Legal Metrology Rules 2011 Compliance
=============================================================================
FastAPI server combining:
1. OpenCV Image Preprocessing (CLAHE, Bilateral filtering, Deskewing)
2. PaddleOCR Text Extraction with Angle Classification
3. Regex & NLP Semantic Entity Parser
4. Statutory Legal Metrology (Packaged Commodities) Rules, 2011 Validation Engine
"""

import os
import time
import logging
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from services.image_preprocessor import ImagePreprocessor
from services.ocr_engine import OCREngine
from services.nlp_parser import NLPParser
from services.rule_validator import LegalMetrologyValidator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("legal_metrology_ai")

# Initialize FastAPI App
app = FastAPI(
    title="LegalLens AI - Legal Metrology Rules 2011 Microservice",
    description="Automated Optical Label Verification & Statutory Metrology Compliance Engine for India",
    version="1.0.0"
)

# Enable Universal Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services (Singletons)
logger.info("Initializing AI Microservice pipelines...")
preprocessor = ImagePreprocessor(target_max_dim=1800, target_min_dim=600)
ocr_engine = OCREngine(use_gpu=False, lang="en")
nlp_parser = NLPParser()
rule_validator = LegalMetrologyValidator()
logger.info("✓ All core AI pipelines ready.")


# Pydantic Schemas for Direct Validation
class ValidateTextRequest(BaseModel):
    text: Optional[str] = None
    lines: Optional[List[str]] = None
    parsed_entities: Optional[Dict[str, Any]] = None


# -------------------------------------------------------------
# Health Check & Service Metadata
# -------------------------------------------------------------
@app.get("/")
def root():
    return {
        "service": "LegalLens Python AI Microservice",
        "status": "ONLINE",
        "regulations": "Legal Metrology (Packaged Commodities) Rules, 2011 (India)",
        "ocr_engine": ocr_engine.engine_type,
        "supported_endpoints": [
            "POST /api/v1/extract (Multipart image upload)",
            "POST /api/v1/validate (Direct text / entity JSON validation)",
            "GET /api/v1/rules (Statutory catalog of rules)"
        ],
        "timestamp": time.time()
    }


@app.get("/healthz")
def healthz():
    return {"status": "OK", "timestamp": time.time()}


# -------------------------------------------------------------
# CORE ENDPOINT: POST /api/v1/extract (Called by Node.js Gateway)
# -------------------------------------------------------------
@app.post("/api/v1/extract")
async def extract_and_validate(
    file: UploadFile = File(...),
    include_preview: bool = Query(False, description="Return base64 enhanced preview image")
):
    """
    Primary API Endpoint:
    1. Ingests uploaded image file buffer.
    2. Runs OpenCV preprocessing (CLAHE, deskew, denoise).
    3. Runs PaddleOCR to extract text lines & bounding boxes.
    4. Runs Regex + NLP parser to extract mandatory packaging entities.
    5. Validates against all Legal Metrology Rules, 2011.
    """
    start_time = time.time()
    try:
        # Validate MIME type
        if file.content_type and not file.content_type.startswith("image/"):
            logger.warning(f"Non-image upload received: {file.content_type}")

        # Read binary file content
        image_bytes = await file.read()
        if not image_bytes or len(image_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Step 1: OpenCV Preprocessing
        logger.info(f"Processing image: {file.filename} ({len(image_bytes)} bytes)")
        prep_result = preprocessor.preprocess(image_bytes)

        # Step 2: PaddleOCR Extraction
        ocr_result = ocr_engine.extract_text(prep_result["ocr_ready_image"])

        # Step 3: Regex & NLP Semantic Parsing
        parsed_entities = nlp_parser.parse(
            ocr_result["raw_text_lines"],
            ocr_result["full_text"]
        )

        # Step 4: Legal Metrology Rules 2011 Validation Engine
        compliance_audit = rule_validator.validate(
            parsed_entities,
            ocr_result["full_text"],
            ocr_result["bounding_boxes"]
        )

        # Optional preview base64
        preview_b64 = None
        if include_preview:
            preview_b64 = preprocessor.image_to_base64(prep_result["ocr_ready_image"])

        latency_ms = round((time.time() - start_time) * 1000, 2)

        # Standardized Response Payload (Aligned with Node.js inspect.js and React ResultView)
        return {
            "success": True,
            "filename": file.filename,
            "ocr_engine_used": ocr_result["ocr_engine_used"],
            "raw_text_lines": ocr_result["raw_text_lines"],
            "full_text": ocr_result["full_text"],
            "parsed_entities": parsed_entities,
            "extracted_fields": parsed_entities,
            "bounding_boxes": ocr_result["bounding_boxes"],
            "compliance_audit": compliance_audit,
            "preprocessing_metadata": {
                "original_dims": prep_result["original_dims"],
                "processed_dims": prep_result["processed_dims"],
                "scale_factor": prep_result["scale_factor"],
                "skew_angle": prep_result["skew_angle"],
                "clahe_applied": True,
                "denoising_applied": True
            },
            "preview_base64": preview_b64,
            "processing_time_ms": latency_ms
        }

    except HTTPException as he:
        raise he
    except Exception as err:
        logger.error(f"Error during inspection processing: {err}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Image inspection failed: {str(err)}")


# -------------------------------------------------------------
# DIRECT VALIDATION ENDPOINT: POST /api/v1/validate
# -------------------------------------------------------------
@app.post("/api/v1/validate")
def validate_entities_or_text(payload: ValidateTextRequest):
    """
    Validates pre-extracted packaging text or structured entities directly
    without requiring an image re-upload.
    """
    if payload.parsed_entities:
        parsed = payload.parsed_entities
        full_text = payload.text or ""
    elif payload.text or payload.lines:
        lines = payload.lines or (payload.text.split("\n") if payload.text else [])
        full_text = payload.text or "\n".join(lines)
        parsed = nlp_parser.parse(lines, full_text)
    else:
        raise HTTPException(status_code=400, detail="Provide either 'parsed_entities', 'text', or 'lines'.")

    audit = rule_validator.validate(parsed, full_text)
    return {
        "success": True,
        "parsed_entities": parsed,
        "compliance_audit": audit
    }


# -------------------------------------------------------------
# STATUTORY RULES CATALOG: GET /api/v1/rules
# -------------------------------------------------------------
@app.get("/api/v1/rules")
def list_metrology_rules():
    """Returns statutory catalog of Legal Metrology (Packaged Commodities) Rules, 2011."""
    return {
        "regulation": "Legal Metrology (Packaged Commodities) Rules, 2011 (India)",
        "parent_act": "The Legal Metrology Act, 2009 (Act No. 1 of 2010)",
        "rules": [
            {
                "rule": "Rule 6(1)(a)",
                "title": "Manufacturer, Packer, and Importer Identity",
                "mandate": "Name and complete postal address of the manufacturer, packer, or importer must be clearly declared.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 6(1)(b)",
                "title": "Generic / Common Name",
                "mandate": "Common or generic names of the commodity contained in the package must be prominently stated.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 6(1)(c) & Rule 12 & Rule 13",
                "title": "Net Quantity & Standard SI Units",
                "mandate": "Net quantity in standard SI units (g, kg, ml, l, N). Non-standard units (gm, gms, kilo, ltr, ml.) are strictly prohibited.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 6(1)(d)",
                "title": "Month & Year of Manufacture / Packing",
                "mandate": "Month and year of manufacture, packing, or import must be printed in MM/YYYY or Month YYYY format.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 6(1)(e)",
                "title": "Maximum Retail Price (MRP) & Tax Syntax",
                "mandate": "MRP declaration must state 'inclusive of all taxes'. Misleading terms like 'Taxes Extra' are prohibited.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 6(1)(f)",
                "title": "Consumer Care Contact Mechanism",
                "mandate": "Name, address, telephone number, and email address of person/office to contact for consumer complaints.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 6(10)",
                "title": "Mandatory Country of Origin",
                "mandate": "Country of origin must be declared conspicuously on all pre-packaged commodities.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 6(11)",
                "title": "Unit Sale Price (USP) (2022 Amendment)",
                "mandate": "Mandatory unit sale price (per g, per kg, per ml, per l, per N) for packages exceeding 1 kg or 1 liter.",
                "penalty_section": "Section 36(1)"
            },
            {
                "rule": "Rule 11",
                "title": "Prohibition of Qualifying Words",
                "mandate": "No qualifying words such as 'approximate', 'when packed', or 'net weight around' shall be stated.",
                "penalty_section": "Section 36(1)"
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
