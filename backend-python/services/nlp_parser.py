"""
Regex & NLP Semantic Entity Parser for Legal Metrology AI Microservice
======================================================================
Parses raw OCR text lines and bounding boxes to extract mandatory declarations
prescribed under the Legal Metrology (Packaged Commodities) Rules, 2011 (India).
Extracts:
- Maximum Retail Price (MRP), currency, tax syntax, Unit Sale Price (USP)
- Net Quantity, magnitude, unit symbol, and non-standard unit detection
- Manufacturing Date (DOM), Packaging Date (PKD), Expiry / Best Before
- Manufacturer, Packer, and Importer postal names, addresses, and PIN codes
- Consumer Care contact details (Email, Phone/Toll-Free, Postal contact)
- Country of Origin
- Commodity / Generic Product Name
- Batch / Lot Number
"""

import re
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("nlp_parser")


class NLPParser:
    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        # 1. MRP & Price Patterns
        self.mrp_pattern = re.compile(
            r'(?:M\.?R\.?P\.?|MAX(?:IMUM)?\s*RETAIL\s*PRICE|MAX\s*PRICE|PRICE|R\.?P\.?)'
            r'[\s:.\-–—]*'
            r'(?:RS\.?|INR|₹)?[\s]*'
            r'([0-9]+(?:[.,][0-9]{1,2})?)'
            r'([^\n]*)',
            re.IGNORECASE
        )
        self.standalone_price = re.compile(
            r'(?:RS\.?|₹|INR)[\s]*([0-9]+(?:[.,][0-9]{1,2})?)',
            re.IGNORECASE
        )
        self.tax_inclusive_pattern = re.compile(
            r'(?:INCL(?:USIVE)?\.?\s*(?:OF)?\s*ALL\s*TAX(?:ES)?|ALL\s*TAX(?:ES)?\s*INCL(?:USIVE)?)',
            re.IGNORECASE
        )
        self.tax_extra_pattern = re.compile(
            r'(?:TAX(?:ES)?\s*EXTRA|LOCAL\s*TAX(?:ES)?\s*EXTRA|PLUS\s*TAX(?:ES)?)',
            re.IGNORECASE
        )
        self.usp_pattern = re.compile(
            r'(?:U\.?S\.?P\.?|UNIT\s*(?:SALE)?\s*PRICE)[\s:.\-–—]*'
            r'(?:RS\.?|₹|INR)?[\s]*([0-9]+(?:[.,][0-9]{1,2})?)'
            r'[\s]*(?:PER|/|EVERY)[\s]*([0-9]*[\s]*(?:g|gm|gms|kg|ml|l|ltr|meter|m|cm|piece|pc|N|U))',
            re.IGNORECASE
        )

        # 2. Net Quantity Patterns (Handles optional qualifying words like approx/around)
        self.net_qty_pattern = re.compile(
            r'(?:NET\s*(?:QTY|QUANTITY|WT|WEIGHT|CONTENTS?|VOL(?:UME)?)?)'
            r'[\s:.\-–—]*'
            r'(?:(?:APPROX(?:IMATE(?:LY)?)?|ABOUT|AROUND|WHEN\s*PACKED)[\s:.\-–—]*)?'
            r'([0-9]+(?:[.,][0-9]+)?)'
            r'[\s]*'
            r'(KGS?|KILOS?|GMS?|GM\.?|G\.?|M\.L\.?|ML\.?|LTRS?|LTR\.?|L\.?|METERS?|MTR|CM|MM|UNITS?|PCS?|PIECES?|N|U)(?=\s|$|[.,;:\)]|\b)',
            re.IGNORECASE
        )
        self.standalone_qty_pattern = re.compile(
            r'\b([0-9]+(?:[.,][0-9]+)?)[\s]*'
            r'(KGS?|KILOS?|GMS?|GM\.?|G\.?|M\.L\.?|ML\.?|LTRS?|LTR\.?|L\.?|METERS?|MTR|CM|MM|UNITS?|PCS?|PIECES?|N|U)(?=\s|$|[.,;:\)]|\b)',
            re.IGNORECASE
        )
        self.approx_qty_pattern = re.compile(
            r'\b(?:APPROX(?:IMATE(?:LY)?)?|WHEN\s*PACKED|WHEN\s*FILLED|ABOUT|AROUND)\b',
            re.IGNORECASE
        )

        # 3. Date Patterns (Mfg / Pkd / Exp / Best Before)
        self.mfg_date_pattern = re.compile(
            r'(?:MFG(?:\s*DATE)?|MFD|DATE\s*OF\s*MFG|PACKED(?:\s*DATE)?|PKD|DATE\s*OF\s*PKD|DATE\s*OF\s*PACKAGING|DOM|B\.?DATE)'
            r'[\s:.\-–—]*'
            r'([0-9]{1,2}[\/\-\.][0-9]{4}|[0-9]{1,2}[\/\-\.][0-9]{2}|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[a-z]*[\s,\.\/\-]+[0-9]{2,4}|[0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})',
            re.IGNORECASE
        )
        self.exp_date_pattern = re.compile(
            r'(?:EXP(?:IRY)?(?:\s*DATE)?|EXP\.?|USE\s*BY|BEFORE\s*DATE)'
            r'[\s:.\-–—]*'
            r'([0-9]{1,2}[\/\-\.][0-9]{4}|[0-9]{1,2}[\/\-\.][0-9]{2}|(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)[a-z]*[\s,\.\/\-]+[0-9]{2,4}|[0-9]{1,2}[\/\-\.][0-9]{1,2}[\/\-\.][0-9]{2,4})',
            re.IGNORECASE
        )
        self.best_before_pattern = re.compile(
            r'(?:BEST\s*BEFORE)[\s:.\-–—]*([0-9]+\s*(?:DAYS?|MONTHS?|YEARS?)[^\n\.,]*)',
            re.IGNORECASE
        )

        # 4. Consumer Care Patterns
        self.email_pattern = re.compile(
            r'\b([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)\b'
        )
        self.phone_pattern = re.compile(
            r'(?:(?:TEL|PHONE|CALL|MOB(?:ILE)?|TOLL[\s\-]*FREE|HELPLINE|NO)[\s:.\-–—]*)?'
            r'((?:1800[\s\-]*[0-9]{3}[\s\-]*[0-9]{4})|(?:\+?91[\s\-]*)?[6-9][0-9]{9}|(?:0[0-9]{2,4}[\s\-]*)?[0-9]{6,8})',
            re.IGNORECASE
        )

        # 5. PIN Code (India Postal Index Number)
        self.pincode_pattern = re.compile(r'\b([1-9][0-9]{2}\s?[0-9]{3})\b')

        # 6. Country of Origin Pattern
        self.origin_pattern = re.compile(
            r'(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|PRODUCT\s*OF|PRODUCED\s*IN)[\s:.\-–—]*([a-zA-Z\s]{2,20})',
            re.IGNORECASE
        )

        # 7. Batch / Lot Number Pattern
        self.batch_pattern = re.compile(
            r'(?:BATCH(?:\s*NO)?|LOT(?:\s*NO)?|B\.?\s*NO\.?)[\s:.\-–—]*([A-Z0-9\-\/]+)',
            re.IGNORECASE
        )

        # 8. Manufacturer Trigger Keywords
        self.mfg_keywords = [
            'manufactured by', 'mfd by', 'mfd. by', 'packed by', 'pkd by', 'pkd. by',
            'marketed by', 'mktd by', 'mktd. by', 'imported by', 'mfg & pkd by',
            'manufacturer', 'packer', 'importer', 'factory address', 'works:'
        ]

    def parse(self, text_lines: List[str], full_text: str = "") -> Dict[str, Any]:
        """
        Main entry point for parsing extracted text lines.
        Returns a structured dictionary of parsed entities and metadata.
        """
        if not full_text and text_lines:
            full_text = "\n".join(text_lines)

        entities: Dict[str, Any] = {
            "mrp_raw": None,
            "mrp_value": None,
            "currency": None,
            "tax_inclusive": False,
            "tax_extra_detected": False,
            "unit_sale_price": None,
            "net_qty_raw": None,
            "net_qty_value": None,
            "net_qty_unit": None,
            "is_non_standard_unit": False,
            "non_standard_unit_found": None,
            "has_qualifying_words": False,
            "mfg_date_raw": None,
            "expiry_date_raw": None,
            "best_before_raw": None,
            "consumer_care_email": None,
            "consumer_care_phone": None,
            "consumer_care_address": None,
            "manufacturer_details": None,
            "packer_details": None,
            "importer_details": None,
            "country_of_origin": None,
            "product_name": None,
            "batch_number": None
        }

        # Step 1: Line-by-line targeted scan
        for idx, line in enumerate(text_lines):
            clean_line = line.strip()
            if not clean_line:
                continue

            # Check MRP
            if not entities["mrp_raw"]:
                mrp_match = self.mrp_pattern.search(clean_line)
                if mrp_match:
                    price_str = mrp_match.group(1).replace(',', '')
                    entities["mrp_value"] = float(price_str)
                    entities["mrp_raw"] = clean_line
                    entities["currency"] = "₹" if "₹" in clean_line else "Rs."

            # Check Unit Sale Price (USP)
            if not entities["unit_sale_price"]:
                usp_match = self.usp_pattern.search(clean_line)
                if usp_match:
                    entities["unit_sale_price"] = usp_match.group(0).strip()

            # Check Net Quantity
            if not entities["net_qty_raw"]:
                qty_match = self.net_qty_pattern.search(clean_line)
                if qty_match:
                    val_str = qty_match.group(1).replace(',', '')
                    entities["net_qty_value"] = float(val_str)
                    entities["net_qty_unit"] = qty_match.group(2).strip().lower()
                    entities["net_qty_raw"] = clean_line

            # Check Manufacturing Date
            if not entities["mfg_date_raw"]:
                mfg_match = self.mfg_date_pattern.search(clean_line)
                if mfg_match:
                    entities["mfg_date_raw"] = mfg_match.group(0).strip()

            # Check Expiry Date
            if not entities["expiry_date_raw"]:
                exp_match = self.exp_date_pattern.search(clean_line)
                if exp_match:
                    entities["expiry_date_raw"] = exp_match.group(0).strip()

            # Check Best Before
            if not entities["best_before_raw"]:
                bb_match = self.best_before_pattern.search(clean_line)
                if bb_match:
                    entities["best_before_raw"] = bb_match.group(0).strip()

            # Check Batch Number
            if not entities["batch_number"]:
                batch_match = self.batch_pattern.search(clean_line)
                if batch_match:
                    entities["batch_number"] = batch_match.group(1).strip()

            # Check Country of Origin
            if not entities["country_of_origin"]:
                origin_match = self.origin_pattern.search(clean_line)
                if origin_match:
                    entities["country_of_origin"] = origin_match.group(1).strip().title()

        # Step 1b: Fallback for Net Quantity if line scan didn't pick it up
        if not entities["net_qty_raw"]:
            qty_match = self.standalone_qty_pattern.search(full_text)
            if qty_match:
                val_str = qty_match.group(1).replace(',', '')
                entities["net_qty_value"] = float(val_str)
                entities["net_qty_unit"] = qty_match.group(2).strip().lower()
                entities["net_qty_raw"] = qty_match.group(0).strip()

        # Step 2: Global text scans for Consumer Care (Email & Phone)
        email_match = self.email_pattern.search(full_text)
        if email_match:
            entities["consumer_care_email"] = email_match.group(1).strip()

        phone_matches = self.phone_pattern.findall(full_text)
        if phone_matches:
            # Filter valid phone numbers (10 digits or 1800 toll free)
            for p in phone_matches:
                digits_only = re.sub(r'[^0-9]', '', p)
                if len(digits_only) >= 8:
                    entities["consumer_care_phone"] = p.strip()
                    break

        # Step 3: Tax Syntax Verification (Rule 6(1)(e))
        if self.tax_inclusive_pattern.search(full_text):
            entities["tax_inclusive"] = True
        if self.tax_extra_pattern.search(full_text):
            entities["tax_extra_detected"] = True

        # Step 4: Unit Standard Verification (Rule 13)
        check_target = (entities["net_qty_raw"] or "") + " " + full_text
        non_standard_list = ['gms', 'gm', 'gm.', 'kilo', 'kilos', 'ltrs', 'ltr', 'ltr.', 'ml.', 'm.l.', 'cc', 'ctn']
        for bad_unit in non_standard_list:
            # Escaped pattern handling punctuation boundary
            pattern = r'(?:^|\s|\d)' + re.escape(bad_unit) + r'(?:\s|$|[.,;:\)]|\b)'
            if re.search(pattern, check_target, re.IGNORECASE):
                entities["is_non_standard_unit"] = True
                entities["non_standard_unit_found"] = bad_unit
                break

        # Check for prohibited qualifying words (Rule 11)
        if self.approx_qty_pattern.search(full_text) or (entities["net_qty_raw"] and self.approx_qty_pattern.search(entities["net_qty_raw"])):
            entities["has_qualifying_words"] = True

        # Step 5: Multi-line Contextual Grouping for Manufacturer Details
        entities["manufacturer_details"] = self._extract_manufacturer_block(text_lines, full_text)

        # Step 6: Product / Commodity Name Heuristic
        entities["product_name"] = self._extract_product_name(text_lines)

        # Default country of origin fallback if "India" or Indian PIN code is detected
        if not entities["country_of_origin"]:
            if re.search(r'\bindia\b', full_text, re.IGNORECASE) or self.pincode_pattern.search(full_text):
                entities["country_of_origin"] = "India (Inferred from Postal Code/Address)"

        return entities

    def _extract_manufacturer_block(self, lines: List[str], full_text: str) -> Optional[str]:
        """
        Uses sliding window contextual NLP to extract manufacturer name,
        industrial area/estate, city, and 6-digit postal PIN code.
        """
        mfg_lines = []
        capturing = False

        for line in lines:
            line_lower = line.lower().strip()
            
            # Start capturing upon encountering manufacturer keyword
            if any(kw in line_lower for kw in self.mfg_keywords):
                capturing = True
                mfg_lines.append(line.strip())
                continue

            if capturing:
                # Stop if encountering next distinct mandatory section
                if any(kw in line_lower for kw in ['net wt', 'net qty', 'mrp', 'batch', 'best before', 'consumer care']):
                    break
                mfg_lines.append(line.strip())
                # If we captured an address with a 6-digit PIN code, that marks the end of postal address
                if self.pincode_pattern.search(line):
                    break
                # Limit to 4 address lines max
                if len(mfg_lines) >= 4:
                    break

        if mfg_lines:
            return ", ".join(mfg_lines)

        # Fallback: search for PIN code vicinity
        pin_match = self.pincode_pattern.search(full_text)
        if pin_match:
            # Extract line containing PIN code
            for line in lines:
                if pin_match.group(1) in line:
                    return line.strip()

        return None

    def _extract_product_name(self, lines: List[str]) -> Optional[str]:
        """
        Extracts prominent product title from first few lines,
        skipping common header words and symbols.
        """
        for line in lines[:4]:
            clean = line.strip()
            # Ignore lines that are prices, dates, or pure numbers
            if len(clean) > 3 and not any(kw in clean.lower() for kw in ['mrp', 'rs.', '₹', 'net', 'batch', 'mfg']):
                return clean
        return "Packaged Commodity Item"
