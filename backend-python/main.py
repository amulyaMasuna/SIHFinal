import io
import re
import os
import cv2
import numpy as np
from PIL import Image
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(
    title="SIH26034 Legal Metrology AI Microservice",
    description="OpenCV Preprocessing + PaddleOCR (PP-OCRv4) Multilingual Extraction Engine"
)

# Enable CORS for React Frontend & Node.js API Gateway
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Primary OCR Engine: PaddleOCR (PP-OCRv4)
print("Initializing Primary OCR Engine: PaddleOCR (PP-OCRv4)...")
ocr_engine = None
ocr_type = "NONE"

try:
    from paddleocr import PaddleOCR
    # Initialize PaddleOCR with direction classification enabled
    ocr_engine = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
    ocr_type = "PADDLE_OCR"
    print("✓ PaddleOCR (PP-OCRv4) engine loaded successfully!")
except Exception as e1:
    print(f"PaddleOCR load notice ({e1}). Fallback to EasyOCR...")
    try:
        import easyocr
        ocr_engine = easyocr.Reader(['en'], gpu=False)
        ocr_type = "EASY_OCR"
        print("✓ EasyOCR fallback engine initialized successfully!")
    except Exception as e2:
        print(f"EasyOCR fallback notice ({e2}). Using OpenCV Contour Analysis.")
        ocr_type = "OPENCV_CONTOUR"

# -------------------------------------------------------------
# OPENCV IMAGE PREPROCESSING PIPELINE
# -------------------------------------------------------------
def preprocess_image(image_bytes: bytes):
    # Decode image bytes to OpenCV BGR matrix
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        raise ValueError("Could not decode image bytes.")
        
    # 1. Adaptive Resizing (Normalize max dimension to 1280px)
    h, w = img.shape[:2]
    max_dim = 1280
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
    # 2. Grayscale Conversion
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 3. CLAHE Contrast Boost (Fixes Glare, Shadows, Dark Packaging)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    
    # 4. Bilateral Filtering (Edge-preserving noise reduction)
    denoised = cv2.bilateralFilter(enhanced, d=5, sigmaColor=75, sigmaSpace=75)
    
    return img, denoised

# -------------------------------------------------------------
# REGEX & ENTITY PARSING ENGINE
# -------------------------------------------------------------
def parse_legal_metrology_entities(text_lines):
    full_text = " \n ".join(text_lines)
    
    # MRP Regex (Captures ₹, Rs., MRP, Max Retail Price)
    mrp_match = re.search(r'(m\.?r\.?p\.?|max\.?\s*retail\s*price|price).*?([\₹\Rs\.]*\s*\d+(\.\d{1,2})?)', full_text, re.IGNORECASE)
    
    # Net Quantity Regex (Captures g, gms, kg, ml, l, Litre, Net Wt, Net Qty)
    net_qty_match = re.search(r'(net\s*(wt|quantity|vol|qty)?[:\.]?)\s*(\d+(\.\d+)?)\s*([a-zA-Z]+)', full_text, re.IGNORECASE)
    if not net_qty_match:
        net_qty_match = re.search(r'(\d+(\.\d+)?)\s*(gms?|g|kg|ml|l|ltr|litres?|n\.w\.)', full_text, re.IGNORECASE)

    # Mfg / Packing Date Regex
    mfg_date_match = re.search(r'(mfg|pkd|packed|mfd|date)[:\.]?\s*(\d{2}[/\-]\d{4}|\w+\s*\d{4}|\d{2}/\d{2}/\d{2,4})', full_text, re.IGNORECASE)
    
    # Consumer Care Email Regex
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
    
    # Consumer Care Phone Regex
    phone_match = re.search(r'(1800\d{6,7}|\+?91[\-\s]?\d{10}|\d{3,5}[\-\s]?\d{6,8})', full_text)
    
    # Country of Origin Regex
    origin_match = re.search(r'(country\s*of\s*origin|made\s*in|product\s*of)[:\.]?\s*([a-zA-Z]+)', full_text, re.IGNORECASE)
    
    # Manufacturer Address Lines
    mfr_match = re.search(r'(mfd\s*by|packed\s*by|marketed\s*by|manufactured\s*by)[:\.]?\s*(.*?)(?=\n|$)', full_text, re.IGNORECASE)

    return {
        "mrp_raw": mrp_match.group(0) if mrp_match else None,
        "net_qty_raw": net_qty_match.group(0) if net_qty_match else None,
        "mfg_date_raw": mfg_date_match.group(0) if mfg_date_match else None,
        "consumer_care_email": email_match.group(0) if email_match else None,
        "consumer_care_phone": phone_match.group(0) if phone_match else None,
        "country_of_origin": origin_match.group(2) if origin_match else None,
        "manufacturer_details": mfr_match.group(0) if mfr_match else None,
        "full_text_sample": full_text[:300]
    }

# -------------------------------------------------------------
# FASTAPI ENDPOINTS
# -------------------------------------------------------------
@app.get("/")
def health_check():
    return {
        "service": "SIH26034 AI Microservice",
        "status": "ONLINE",
        "ocr_engine_active": ocr_type
    }

@app.post("/api/v1/extract")
async def extract_and_parse(file: UploadFile = File(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a valid image.")
        
    image_bytes = await file.read()
    
    try:
        original_img, clean_img = preprocess_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image preprocessing failed: {str(e)}")
        
    extracted_lines = []
    bounding_boxes = []
    
    # 1. PADDLE_OCR (PP-OCRv4) PRIMARY EXTRACTION PIPELINE
    if ocr_type == "PADDLE_OCR" and ocr_engine:
        try:
            ocr_res = ocr_engine.ocr(clean_img, cls=True)
            if ocr_res and ocr_res[0]:
                for line in ocr_res[0]:
                    box = line[0]  # 4-point polygon coordinates [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
                    text = line[1][0]
                    conf = float(line[1][1])
                    if conf > 0.30 and len(text.strip()) > 0:
                        extracted_lines.append(text)
                        bounding_boxes.append({
                            "text": text,
                            "box": box,
                            "confidence": round(conf, 2)
                        })
        except Exception as e:
            print(f"PaddleOCR runtime error ({e})")

    # 2. EASY_OCR FALLBACK EXTRACTION
    elif ocr_type == "EASY_OCR" and ocr_engine:
        try:
            ocr_res = ocr_engine.readtext(clean_img)
            for bbox, text, conf in ocr_res:
                if conf > 0.25 and len(text.strip()) > 0:
                    extracted_lines.append(text)
                    coords = [[int(pt[0]), int(pt[1])] for pt in bbox]
                    bounding_boxes.append({"text": text, "box": coords, "confidence": round(float(conf), 2)})
        except Exception as e:
            print(f"EasyOCR runtime error ({e})")

    # 3. OPENCV CONTOUR + BLOB ANALYSIS (FALLBACK)
    if not extracted_lines:
        edges = cv2.Canny(clean_img, 100, 200)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
        dilated = cv2.dilate(edges, kernel, iterations=2)
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 40 and h > 12:
                bounding_boxes.append({
                    "text": "Extracted Text Region",
                    "box": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
                    "confidence": 0.85
                })

    # Parse Legal Entities from Extracted Lines
    parsed_entities = parse_legal_metrology_entities(extracted_lines)
    
    return {
        "ocr_engine_used": ocr_type,
        "raw_text_lines": extracted_lines,
        "parsed_entities": parsed_entities,
        "bounding_boxes": bounding_boxes
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
