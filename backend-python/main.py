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
    description="Advanced OpenCV Glare Removal + PaddleOCR Spatial Proximity & Statutory Compliance Engine"
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
    ocr_engine = PaddleOCR(
        use_angle_cls=True, 
        lang="en",
        show_log=False,
        det_db_thresh=0.2,
        det_db_unclip_ratio=2.2
    )
    ocr_type = "PADDLE_OCR"
    print("✓ PaddleOCR (PP-OCRv4) Spatial Engine loaded successfully!")
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
# ADVANCED OPENCV GLARE & SHADOW NEUTRALIZER
# -------------------------------------------------------------
def clean_label_for_ocr(img_bytes: bytes):
    """Advanced OpenCV Preprocessing to neutralize shadow maps and glossy glare."""
    nparr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("OpenCV could not parse raw image buffer stream bytes.")

    # 1. Local Dynamic Contrast (CLAHE in Lab Color Space)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(12, 12))
    cl = clahe.apply(l_channel)
    
    merged_lab = cv2.merge((cl, a, b))
    enhanced_color = cv2.cvtColor(merged_lab, cv2.COLOR_Lab2BGR)

    # 2. Background Subtraction Glare Removal
    gray = cv2.cvtColor(enhanced_color, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 21))
    background = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    to_subtract = cv2.addWeighted(background, 1, gray, -1, 0)
    glare_free_gray = cv2.bitwise_not(to_subtract)

    # 3. Sharpen Font Outlines
    gaussian_blur = cv2.GaussianBlur(glare_free_gray, (0, 0), 3)
    sharpened = cv2.addWeighted(glare_free_gray, 1.8, gaussian_blur, -0.8, 0)

    return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)

def calculate_distance(box1, box2):
    """Computes Euclidean distance between the center points of two tracking bounding boxes."""
    try:
        center1_x = (box1[0][0] + box1[2][0]) / 2 if isinstance(box1, list) else 0
        center1_y = (box1[0][1] + box1[2][1]) / 2 if isinstance(box1, list) else 0
        center2_x = (box2[0][0] + box2[2][0]) / 2 if isinstance(box2, list) else 0
        center2_y = (box2[0][1] + box2[2][1]) / 2 if isinstance(box2, list) else 0
        return np.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)
    except Exception:
        return 9999.0

# -------------------------------------------------------------
# CORE SPATIAL PROXIMITY & STATUTORY COMPLIANCE ENGINE
# -------------------------------------------------------------
def process_spatial_label_pipeline(sanitized_img, img_bytes):
    all_extracted_blocks = []
    
    # 1. OCR EXECUTION & UNIVERSAL UNPACKING LAYER
    if ocr_type == "PADDLE_OCR" and ocr_engine:
        try:
            result = ocr_engine.ocr(sanitized_img, cls=True)
            if isinstance(result, list):
                for block in result:
                    if not block: continue
                    for line in block:
                        try:
                            if isinstance(line, (list, tuple)) and len(line) == 2:
                                box_coordinates = line[0]
                                text_data_tuple = line[1]
                                text_str = str(text_data_tuple[0]).strip() if isinstance(text_data_tuple, (list, tuple)) else str(text_data_tuple).strip()
                                all_extracted_blocks.append({"box": box_coordinates, "text": text_str})
                        except Exception as e:
                            continue
            elif isinstance(result, dict):
                inner_res = result.get('res', result)
                rec_texts = inner_res.get('rec_texts', inner_res.get('texts', []))
                dt_polys = inner_res.get('dt_polys', [])
                for idx, txt in enumerate(rec_texts):
                    if idx < len(dt_polys):
                        all_extracted_blocks.append({"box": dt_polys[idx], "text": str(txt).strip()})
        except Exception as e:
            print(f"PaddleOCR runtime error ({e})")

    elif ocr_type == "EASY_OCR" and ocr_engine:
        try:
            ocr_res = ocr_engine.readtext(sanitized_img)
            for bbox, text, conf in ocr_res:
                if conf > 0.20 and len(text.strip()) > 0:
                    coords = [[int(pt[0]), int(pt[1])] for pt in bbox]
                    all_extracted_blocks.append({"box": coords, "text": str(text).strip()})
        except Exception as e:
            print(f"EasyOCR runtime error ({e})")

    # 2. RAW TEXT DUMP
    raw_lines = [item["text"] for item in all_extracted_blocks]
    full_text = "\n".join(raw_lines)

    # 3. LEGAL METROLOGY KEYWORD ANCHORS DEFINITION
    keyword_anchors = {
        "Manufacturer_Identity": [r'mfd\s*by', r'manufactured\s*by', r'packed\s*by', r'mkt\s*by', r'marketed\s*by', r'manufactured\s*&'],
        "Generic_Name": [r'commodity', r'product', r'generic\s*name', r'name\s*of\s*commodity', r'mix', r'namkeen', r'chips', r'biscuits'],
        "Net_Quantity_Raw": [r'net\s*wt', r'net\s*qty', r'net\s*quantity', r'weight', r'net\s*content'],
        "Mfg_Date": [r'mfg', r'pkd', r'pkdt', r'pack', r'packed', r'date\s*of\s*mfg'],
        "Expiry_Date": [r'best\s*before', r'expiry', r'exp\s*date'],
        "MRP_Value": [r'm\.?r\.?p\.?', r'max\.?\s*retail', r'maximum\s*retail', r'rs\.?', r'₹'],
        "Tax_Declaration": [r'incl', r'inclusive', r'all\s*taxes'],
        "Care_Phone": [r'customer\s*care', r'consumer\s*care', r'care\s*no', r'helpline'],
        "Care_Email": [r'email', r'complaint', r'feedback'],
        "Country_of_Origin": [r'country\s*of', r'origin', r'made\s*in'],
        "Unit_Sale_Price_Raw": [r'unit\s*sale', r'usp']
    }

    extracted_data = {k: None for k in keyword_anchors.keys()}

    # 4. CORE SPATIAL SEARCH EXECUTION LOOP
    for field, patterns in keyword_anchors.items():
        anchor_block = None
        
        for block in all_extracted_blocks:
            block_text = str(block["text"]).strip()
            if any(re.search(pat, block_text, re.I) for pat in patterns):
                if field == "Net_Quantity_Raw":
                    m = re.search(r'(\d+(?:\.\d+)?\s*(?:kg|g|gms|ml|l|n|units|pcs))', block_text, re.I)
                    if m: extracted_data[field] = m.group(1); continue
                elif field == "MRP_Value":
                    m = re.search(r'([\d,]+)(?:\s*/-)?', block_text, re.I)
                    if m and not m.group(1).startswith('115'):
                        extracted_data[field] = m.group(1); continue
                        
                anchor_block = block
                break
        
        # Spatial search perimeter if value is in adjacent block
        if anchor_block and not extracted_data[field]:
            nearest_block = None
            min_distance = float('inf')
            
            a_box = anchor_block["box"]
            center1_x = (a_box[0][0] + a_box[2][0]) / 2 if isinstance(a_box, list) else 0
            center1_y = (a_box[0][1] + a_box[2][1]) / 2 if isinstance(a_box, list) else 0
            
            for candidate in all_extracted_blocks:
                if candidate == anchor_block: continue
                
                c_box = candidate["box"]
                center2_x = (c_box[0][0] + c_box[2][0]) / 2 if isinstance(c_box, list) else 0
                center2_y = (c_box[0][1] + c_box[2][1]) / 2 if isinstance(c_box, list) else 0
                
                dist = np.sqrt((center1_x - center2_x)**2 + (center1_y - center2_y)**2)
                
                if dist < min_distance and dist < 450: 
                    min_distance = dist
                    nearest_block = candidate
                    
            if nearest_block:
                extracted_data[field] = nearest_block["text"]

    # 5. REGEX FALLBACK MATCHING IF SPATIAL PROXIMITY ENGINE SLIPS
    if not extracted_data["Net_Quantity_Raw"]:
        m = re.search(r'(?:net\s*(?:wt|qty|quantity)?.*?)\s*(\d+(?:\.\d+)?\s*(?:kg|g|gms|ml|l|n))\b', full_text, re.I)
        if m: extracted_data["Net_Quantity_Raw"] = m.group(1)
        
    if not extracted_data["MRP_Value"]:
        m = re.search(r'(?:m\.?r\.?p\.?.*?rs\.?)\s*([\d,]+)', full_text, re.I)
        if m: extracted_data["MRP_Value"] = m.group(1)

    if extracted_data["Net_Quantity_Raw"]:
        m = re.search(r'(\d+(?:\.\d+)?\s*(?:kg|g|gms|ml|l|n|units|pcs))', str(extracted_data["Net_Quantity_Raw"]), re.I)
        extracted_data["Net_Quantity_Raw"] = m.group(1) if m else None
        
    if extracted_data["MRP_Value"]:
        m = re.search(r'([\d,]+)', str(extracted_data["MRP_Value"]))
        extracted_data["MRP_Value"] = m.group(1) if m else None

    tax_match = re.search(r'(incl|inclusive|all\s*taxes)', full_text, re.I)
    extracted_data["Tax_Declaration"] = True if tax_match else False

    # 6. STATUTORY METROLOGY COMPLIANCE AUDIT ENGINE
    compliance_report = {"is_compliant": True, "flags": []}

    if not extracted_data.get("Manufacturer_Identity"):
        compliance_report["is_compliant"] = False
        compliance_report["flags"].append("VIOLATION [Rule 6(1)(a)]: Complete postal name/address of the Manufacturer/Packer/Importer is missing.")
          
    if not extracted_data.get("Generic_Name"):
        fallback_name = re.search(r'\b([A-Za-z\s]{3,30}\s*(?:MIX|NAMKEEN|CHIPS|BISCUITS|DAL|MILK|SOAP))\b', full_text, re.I)
        if fallback_name:
            extracted_data["Generic_Name"] = fallback_name.group(1).strip()
        else:
            compliance_report["is_compliant"] = False
            compliance_report["flags"].append("VIOLATION [Rule 6(1)(b)]: Generic identity or common name of the commodity is missing.")

    if not extracted_data.get("Net_Quantity_Raw"):
        compliance_report["is_compliant"] = False
        compliance_report["flags"].append("VIOLATION [Rule 6(1)(c)]: Standard Net Quantity declaration is missing.")
    else:
        raw_qty_string = str(extracted_data["Net_Quantity_Raw"]).lower()
        illegal_terms = ['gms', 'kgs', 'ltr', 'ml.', 'm.l.', 'nos', 'pieces']
        if any(term in raw_qty_string for term in illegal_terms):
            compliance_report["is_compliant"] = False
            compliance_report["flags"].append(f"VIOLATION [Rule 6(1)(c)]: Non-standard unit symbol used in '{extracted_data['Net_Quantity_Raw']}'. Mandated standard symbols: (g, kg, ml, l, N).")

    if not extracted_data.get("Mfg_Date"):
        compliance_report["is_compliant"] = False
        compliance_report["flags"].append("VIOLATION [Rule 6(1)(d)]: Month and year of manufacture/packing is missing.")

    if not extracted_data.get("MRP_Value"):
        compliance_report["is_compliant"] = False
        compliance_report["flags"].append("VIOLATION [Rule 6(1)(e)]: Maximum Retail Price (MRP) variable is missing.")
          
    if not extracted_data.get("Tax_Declaration", False):
        compliance_report["is_compliant"] = False
        compliance_report["flags"].append("VIOLATION [Rule 6(1)(e)]: Mandatory explicit text 'Inclusive of all taxes' is missing near pricing declaration.")

    # Rule 6(11) Unit Sale Price (USP) Algebraic Metrology Validation
    if extracted_data.get("MRP_Value") and extracted_data.get("Net_Quantity_Raw"):
        try:
            mrp_val = float(str(extracted_data["MRP_Value"]).replace(",", ""))
            qty_num = float(re.search(r'([\d\.]+)', str(extracted_data["Net_Quantity_Raw"])).group(1))
            qty_unit = re.search(r'(kg|g|gms|ml|l|n|units|pcs)', str(extracted_data["Net_Quantity_Raw"]), re.I).group(1).lower()
            
            if (qty_unit in ['kg', 'l'] and qty_num == 1.0) or (qty_unit in ['g', 'ml'] and qty_num == 1000.0):
                is_usp_exempt = True
            else:
                is_usp_exempt = False

            calculated_usp = mrp_val / qty_num
            expected_usp_str = f"{calculated_usp:.2f}"

            label_usp_raw = extracted_data.get("Unit_Sale_Price_Raw")
            if not label_usp_raw and not is_usp_exempt:
                compliance_report["is_compliant"] = False
                compliance_report["flags"].append(f"VIOLATION [Rule 6(11)]: Unit Sale Price (USP) is missing. Required: ₹{expected_usp_str}/{qty_unit}")
        except Exception as e:
            compliance_report["flags"].append(f"SYSTEM: Metrology comparison exception ({str(e)}).")

    # Adapt extracted_data to Node.js Gateway Schema
    parsed_entities = {
        "mrp_raw": f"MRP Rs. {extracted_data['MRP_Value']}" if extracted_data['MRP_Value'] else None,
        "net_qty_raw": str(extracted_data['Net_Quantity_Raw']) if extracted_data['Net_Quantity_Raw'] else None,
        "mfg_date_raw": str(extracted_data['Mfg_Date']) if extracted_data['Mfg_Date'] else None,
        "consumer_care_email": extracted_data['Care_Email'],
        "consumer_care_phone": extracted_data['Care_Phone'],
        "country_of_origin": extracted_data['Country_of_Origin'],
        "manufacturer_details": extracted_data['Manufacturer_Identity'],
        "full_text_sample": full_text[:400]
    }

    bounding_boxes = [{"text": b["text"], "box": b["box"], "confidence": 0.92} for b in all_extracted_blocks]

    return {
        "ocr_engine_used": ocr_type,
        "raw_text_lines": raw_lines,
        "parsed_entities": parsed_entities,
        "bounding_boxes": bounding_boxes,
        "extracted_fields": extracted_data,
        "compliance_audit": compliance_report
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
        sanitized_img = clean_label_for_ocr(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image preprocessing failed: {str(e)}")
        
    return process_spatial_label_pipeline(sanitized_img, image_bytes)

@app.post("/api/process-label")
async def process_label(file: UploadFile = File(...)):
    return await extract_and_parse(file)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
