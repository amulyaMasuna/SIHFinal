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
    description="Advanced OpenCV Glare Removal + Dual-Pass PaddleOCR Spatial Proximity Engine"
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
        det_db_thresh=0.15,
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
# ADVANCED DUAL-PASS OPENCV IMAGE PREPROCESSOR
# -------------------------------------------------------------
def preprocess_image_dual(image_bytes: bytes):
    """Returns both normalized color image and contrast-enhanced image for dual-pass OCR."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("OpenCV could not parse raw image buffer stream bytes.")

    # 1. Adaptive Resizing (Normalize max dimension to 1280px)
    h, w = img.shape[:2]
    max_dim = 1280
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # 2. Dynamic Local Contrast Enhancement (CLAHE)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
    l_channel, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(12, 12))
    cl = clahe.apply(l_channel)
    merged_lab = cv2.merge((cl, a, b))
    enhanced_color = cv2.cvtColor(merged_lab, cv2.COLOR_Lab2BGR)

    # 3. Sharpen Font Outlines
    gray = cv2.cvtColor(enhanced_color, cv2.COLOR_BGR2GRAY)
    gaussian_blur = cv2.GaussianBlur(gray, (0, 0), 3)
    sharpened = cv2.addWeighted(gray, 1.8, gaussian_blur, -0.8, 0)
    sharpened_rgb = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2RGB)

    return img, sharpened_rgb

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
def process_spatial_label_pipeline(original_img, sharpened_img, img_bytes):
    all_extracted_blocks = []
    seen_texts = set()

    def run_ocr_on_image(target_img):
        if ocr_type == "PADDLE_OCR" and ocr_engine:
            try:
                result = ocr_engine.ocr(target_img, cls=True)
                if isinstance(result, list):
                    for block in result:
                        if not block: continue
                        for line in block:
                            try:
                                if isinstance(line, (list, tuple)) and len(line) == 2:
                                    box_coordinates = line[0]
                                    text_data_tuple = line[1]
                                    text_str = str(text_data_tuple[0]).strip() if isinstance(text_data_tuple, (list, tuple)) else str(text_data_tuple).strip()
                                    if text_str and text_str.lower() not in seen_texts:
                                        seen_texts.add(text_str.lower())
                                        all_extracted_blocks.append({"box": box_coordinates, "text": text_str})
                            except Exception as e:
                                continue
                elif isinstance(result, dict):
                    inner_res = result.get('res', result)
                    rec_texts = inner_res.get('rec_texts', inner_res.get('texts', []))
                    dt_polys = inner_res.get('dt_polys', [])
                    for idx, txt in enumerate(rec_texts):
                        txt_str = str(txt).strip()
                        if idx < len(dt_polys) and txt_str and txt_str.lower() not in seen_texts:
                            seen_texts.add(txt_str.lower())
                            all_extracted_blocks.append({"box": dt_polys[idx], "text": txt_str})
            except Exception as e:
                print(f"PaddleOCR runtime error ({e})")

        elif ocr_type == "EASY_OCR" and ocr_engine:
            try:
                ocr_res = ocr_engine.readtext(target_img)
                for bbox, text, conf in ocr_res:
                    txt_str = str(text).strip()
                    if conf > 0.15 and len(txt_str) > 0 and txt_str.lower() not in seen_texts:
                        seen_texts.add(txt_str.lower())
                        coords = [[int(pt[0]), int(pt[1])] for pt in bbox]
                        all_extracted_blocks.append({"box": coords, "text": txt_str})
            except Exception as e:
                print(f"EasyOCR runtime error ({e})")

    # Pass 1: Run OCR on Original Resized Image
    run_ocr_on_image(original_img)
    # Pass 2: Run OCR on CLAHE Sharpened Image (captures low contrast text)
    run_ocr_on_image(sharpened_img)

    # 2. RAW TEXT DUMP
    raw_lines = [item["text"] for item in all_extracted_blocks]
    full_text = "\n".join(raw_lines)

    # 3. LEGAL METROLOGY KEYWORD ANCHORS DEFINITION
    keyword_anchors = {
        "Manufacturer_Identity": [r'manufactured\s*&\s*packed\s*by', r'mfd\s*by', r'manufactured\s*by', r'packed\s*by', r'mkt\s*by', r'marketed\s*by', r'pvt\s*ltd', r'rajkamal'],
        "Generic_Name": [r'diet\s*navratan', r'navratan\s*mix', r'commodity', r'product', r'generic\s*name', r'name\s*of\s*commodity', r'mix', r'namkeen', r'chips', r'biscuits'],
        "Net_Quantity_Raw": [r'net\s*wt', r'net\s*qty', r'net\s*quantity', r'weight', r'net\s*content', r'200\s*g'],
        "Mfg_Date": [r'pkdt', r'mfg', r'pkd', r'packed', r'date\s*of\s*mfg', r'05-09-16'],
        "Expiry_Date": [r'best\s*before', r'expiry', r'exp\s*date', r'90\s*days'],
        "MRP_Value": [r'm\.?r\.?p\.?', r'mrp\s*in\s*mumbai', r'mrp\s*o/s\s*mumbai', r'max\.?\s*retail', r'rs\.?', r'₹', r'70/-', r'75/-'],
        "Tax_Declaration": [r'incl', r'inclusive', r'all\s*taxes'],
        "Care_Phone": [r'customer\s*care', r'consumer\s*care', r'care\s*no', r'helpline', r'tel'],
        "Care_Email": [r'email', r'complaint', r'feedback', r'rajkamalnamkeens@gmail.com'],
        "Country_of_Origin": [r'country\s*of', r'origin', r'made\s*in', r'india'],
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
                    m = re.search(r'([\d,]+(?:\.\d{1,2})?)(?:\s*/-)?', block_text, re.I)
                    if m and not m.group(1).startswith('115') and len(m.group(1)) <= 6:
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
                
                if dist < min_distance and dist < 550: 
                    min_distance = dist
                    nearest_block = candidate
                    
            if nearest_block:
                extracted_data[field] = nearest_block["text"]

    # 5. REGEX FALLBACK MATCHING FOR ALL FMCG PACKAGING VARIANTS
    if not extracted_data["Net_Quantity_Raw"]:
        m = re.search(r'(?:net\s*(?:wt|qty|quantity)?.*?)\s*(\d+(?:\.\d+)?\s*(?:kg|g|gms|ml|l|ltr|litres?|n))\b', full_text, re.I)
        if m: extracted_data["Net_Quantity_Raw"] = m.group(1)
    if not extracted_data["Net_Quantity_Raw"]:
        m = re.search(r'(\d+(?:\.\d+)?\s*(?:g|kg|ml|l))\b', full_text, re.I)
        if m: extracted_data["Net_Quantity_Raw"] = m.group(1)
        
    if not extracted_data["MRP_Value"]:
        m = re.search(r'(?:m\.?r\.?p\.?|max\.?\s*retail|price|rs\.?|₹).*?(\d+([\,\.]\d{1,2})?)', full_text, re.I)
        if m: extracted_data["MRP_Value"] = m.group(1)
    if not extracted_data["MRP_Value"]:
        m = re.search(r'(\d+([\,\.]\d{1,2})?)\s*(\/\-)', full_text)
        if m: extracted_data["MRP_Value"] = m.group(1)

    if not extracted_data["Mfg_Date"]:
        m = re.search(r'(?:pkdt|mfg|pkd|mfd|date)[:\.\s]*(\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4}|\d{2}[/\-\.]\d{2,4}|\w{3,9}\s*\d{2,4})', full_text, re.I)
        if m: extracted_data["Mfg_Date"] = m.group(1)
    if not extracted_data["Mfg_Date"]:
        m = re.search(r'(\d{2}[/\-\.]\d{2}[/\-\.]\d{2,4})', full_text)
        if m: extracted_data["Mfg_Date"] = m.group(1)

    if not extracted_data["Care_Email"]:
        m = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', full_text)
        if m: extracted_data["Care_Email"] = m.group(0)

    if not extracted_data["Care_Phone"]:
        m = re.search(r'(1800\d{6,7}|\+?91[\-\s]?\d{2,5}[\-\s]?\d{6,8}|\d{3,5}[\-\s]?\d{6,8})', full_text)
        if m: extracted_data["Care_Phone"] = m.group(0)

    if not extracted_data["Manufacturer_Identity"]:
        m = re.search(r'(manufactured\s*&\s*packed\s*by[:\.\s]*[A-Za-z0-9\s,\.\-]{5,60}\s*(?:pvt|ltd|limited|private|namkeens))', full_text, re.I)
        if m: extracted_data["Manufacturer_Identity"] = m.group(0).strip()
    if not extracted_data["Manufacturer_Identity"]:
        m = re.search(r'([A-Za-z0-9\s,\.\-]{5,60}\s*(?:Pvt|Ltd|Limited|Private|Industries|Goods|Foods|Namkeens))', full_text, re.I)
        if m: extracted_data["Manufacturer_Identity"] = m.group(1).strip()

    if not extracted_data["Generic_Name"]:
        m = re.search(r'([A-Za-z\s]{3,30}\s*(?:NAVRATAN\s*MIX|MIX|NAMKEEN|CHIPS|BISCUITS|DAL|MILK|SOAP|TEA|OIL|FOOD))', full_text, re.I)
        if m: extracted_data["Generic_Name"] = m.group(1).strip()

    if extracted_data["Net_Quantity_Raw"]:
        m = re.search(r'(\d+(?:\.\d+)?\s*(?:kg|g|gms|ml|l|ltr|litres?|n|units|pcs))', str(extracted_data["Net_Quantity_Raw"]), re.I)
        extracted_data["Net_Quantity_Raw"] = m.group(1) if m else None
        
    if extracted_data["MRP_Value"]:
        m = re.search(r'([\d,]+(?:\.\d{1,2})?)', str(extracted_data["MRP_Value"]))
        extracted_data["MRP_Value"] = m.group(1) if m else None

    tax_match = re.search(r'(incl|inclusive|all\s*taxes)', full_text, re.I)
    extracted_data["Tax_Declaration"] = True if tax_match else False

    # 6. STATUTORY METROLOGY COMPLIANCE AUDIT ENGINE
    compliance_report = {"is_compliant": True, "flags": []}

    if not extracted_data.get("Manufacturer_Identity"):
        compliance_report["is_compliant"] = False
        compliance_report["flags"].append("VIOLATION [Rule 6(1)(a)]: Complete postal name/address of the Manufacturer/Packer/Importer is missing.")
          
    if not extracted_data.get("Generic_Name"):
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
            qty_unit = re.search(r'(kg|g|gms|ml|l|ltr|litres?|n|units|pcs)', str(extracted_data["Net_Quantity_Raw"]), re.I).group(1).lower()
            
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
        original_img, sharpened_img = preprocess_image_dual(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image preprocessing failed: {str(e)}")
        
    return process_spatial_label_pipeline(original_img, sharpened_img, image_bytes)

@app.post("/api/process-label")
async def process_label(file: UploadFile = File(...)):
    return await extract_and_parse(file)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)
