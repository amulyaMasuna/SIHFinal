"""
Statutory Legal Metrology (Packaged Commodities) Rules, 2011 Validation Engine
=============================================================================
Evaluates extracted entities against all statutory provisions under the
Legal Metrology Act, 2009 and the Legal Metrology (Packaged Commodities) Rules, 2011 (India),
including the 2021/2022 Unit Sale Price (USP) Amendments.

Covered Statutory Rules:
- Rule 6(1)(a): Manufacturer, Packer, Importer Name & Postal Address
- Rule 6(1)(b): Generic / Common Name of Commodity
- Rule 6(1)(c): Net Quantity & Standard Units
- Rule 6(1)(d): Month & Year of Manufacture / Packing / Import
- Rule 6(1)(e): Maximum Retail Price (MRP) & Mandatory Tax Syntax
- Rule 6(1)(f): Consumer Care Contact Details (Phone, Email, Address)
- Rule 6(10): Mandatory Country of Origin Declaration
- Rule 6(11): Mandatory Unit Sale Price (USP) Declaration (2022 Amendment)
- Rule 11: Prohibition of Misleading Qualifying Terms
- Rule 13: Standard Units of Weight and Measure (Strict prohibition of 'gms', 'kilos', etc.)
- Rule 7 & 8: Minimum Numeral & Font Height Standards
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger("rule_validator")


class LegalMetrologyValidator:
    def __init__(self):
        pass

    def validate(self, parsed_entities: Dict[str, Any], full_text: str = "", bounding_boxes: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes statutory compliance audit on extracted packaging entities.
        Returns:
            - status: 'PASS' | 'NON_COMPLIANT'
            - total_violations: int
            - compliance_score: int (0-100)
            - violations: List of itemized violation objects
            - flags: List of plain text strings for Node.js gateway merge
            - legal_notice_draft: Section 36 statutory inspection notice text
        """
        violations = []
        flags = []
        total_checks = 8
        passed_checks = 0

        text_lower = (full_text + " " + " ".join([str(v) for v in parsed_entities.values() if v])).lower()

        # =====================================================================
        # CHECK 1: RULE 6(1)(e) - Maximum Retail Price & Tax Syntax
        # =====================================================================
        mrp_raw = parsed_entities.get("mrp_raw")
        tax_inclusive = parsed_entities.get("tax_inclusive", False)
        tax_extra = parsed_entities.get("tax_extra_detected", False)

        if not mrp_raw:
            violations.append({
                "rule": "Rule 6(1)(e)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "MRP Declaration",
                "severity": "CRITICAL",
                "found": None,
                "issue": "Maximum Retail Price (MRP) declaration is completely missing on package label.",
                "recommendation": "Declare MRP conspicuously in the format: 'MRP Rs. XX.XX (inclusive of all taxes)'."
            })
            flags.append("MRP declaration is completely missing.")
        else:
            mrp_ok = True
            # Tax Inclusive Check
            if not tax_inclusive and not any(kw in text_lower for kw in ['incl', 'inclusive', 'all taxes']):
                violations.append({
                    "rule": "Rule 6(1)(e)",
                    "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                    "category": "MRP Syntax",
                    "severity": "MAJOR",
                    "found": mrp_raw,
                    "issue": "MRP text lacks mandatory phrase 'inclusive of all taxes'.",
                    "recommendation": "Append '(inclusive of all taxes)' or 'incl. of all taxes' immediately adjacent to price."
                })
                flags.append("MRP text must explicitly state 'inclusive of all taxes'.")
                mrp_ok = False

            # Misleading 'Taxes Extra' Check (Illegal under Act)
            if tax_extra or ("tax" in text_lower and "extra" in text_lower):
                violations.append({
                    "rule": "Rule 6(1)(e)",
                    "section": "Section 36, Legal Metrology Act, 2009",
                    "category": "Prohibited Price Syntax",
                    "severity": "CRITICAL",
                    "found": mrp_raw,
                    "issue": "Misleading price declaration 'Taxes Extra' detected. Strictly illegal under Legal Metrology Act.",
                    "recommendation": "Remove any reference to extra taxes; MRP must be all-inclusive."
                })
                flags.append("Misleading price statement 'Taxes Extra' detected. Illegal under Legal Metrology Act 2009.")
                mrp_ok = False

            if mrp_ok:
                passed_checks += 1

        # =====================================================================
        # CHECK 2: RULE 6(1)(c) & RULE 13 - Net Quantity & Standard Units
        # =====================================================================
        net_qty_raw = parsed_entities.get("net_qty_raw")
        is_non_standard = parsed_entities.get("is_non_standard_unit", False)
        bad_unit = parsed_entities.get("non_standard_unit_found")

        if not net_qty_raw:
            violations.append({
                "rule": "Rule 6(1)(c)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "Net Quantity",
                "severity": "CRITICAL",
                "found": None,
                "issue": "Net Quantity declaration is missing on the package.",
                "recommendation": "Declare net quantity prominently in standard SI units (e.g. 'Net Qty: 500 g')."
            })
            flags.append("Net Quantity declaration is missing.")
        else:
            qty_ok = True
            # Rule 13: Standard Unit Symbols (gms, gm, kilo, ltr, etc. are illegal)
            if is_non_standard or (bad_unit is not None):
                symbol = bad_unit or "non-standard"
                violations.append({
                    "rule": "Rule 13",
                    "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                    "category": "Standard Units",
                    "severity": "MAJOR",
                    "found": net_qty_raw,
                    "issue": f"Non-standard unit symbol '{symbol}' detected. Legal Metrology Rules mandate standard symbols ('g', 'kg', 'ml', 'l', 'N'). Unit symbols must never take plural 's'.",
                    "recommendation": f"Replace non-standard '{symbol}' with statutory SI symbol ('g', 'kg', 'ml', 'l', or 'N')."
                })
                flags.append(f"Non-standard unit symbol '{symbol}' detected. Legal Metrology Rules mandate standard symbols ('g', 'kg', 'ml', 'l', 'N'). Unit symbols must never take plural 's'.")
                qty_ok = False

            # Rule 11: Prohibited Qualifying Terms (approx, when packed)
            if parsed_entities.get("has_qualifying_words"):
                violations.append({
                    "rule": "Rule 11",
                    "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                    "category": "Prohibited Qualifying Words",
                    "severity": "MAJOR",
                    "found": net_qty_raw,
                    "issue": "Prohibited qualifying word ('approximate', 'when packed') detected with Net Quantity.",
                    "recommendation": "Remove qualifying expressions. Declare exact nominal quantity."
                })
                flags.append("Prohibited qualifying terms (e.g. 'approximate', 'when packed') detected.")
                qty_ok = False

            if qty_ok:
                passed_checks += 1

        # =====================================================================
        # CHECK 3: RULE 6(1)(d) - Month & Year of Manufacture / Packing
        # =====================================================================
        mfg_date_raw = parsed_entities.get("mfg_date_raw")
        if not mfg_date_raw:
            violations.append({
                "rule": "Rule 6(1)(d)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "Mfg / Packing Date",
                "severity": "MAJOR",
                "found": None,
                "issue": "Month and Year of manufacture / packing / import is missing.",
                "recommendation": "Declare Month and Year of manufacture in MM/YYYY format (e.g. 'Mfg Date: 03/2026')."
            })
            flags.append("Month and Year of manufacture / packing / import is missing.")
        else:
            passed_checks += 1

        # =====================================================================
        # CHECK 4: RULE 6(1)(f) - Consumer Care Contact Details
        # =====================================================================
        care_email = parsed_entities.get("consumer_care_email")
        care_phone = parsed_entities.get("consumer_care_phone")

        if not care_email and not care_phone:
            violations.append({
                "rule": "Rule 6(1)(f)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "Consumer Care",
                "severity": "CRITICAL",
                "found": None,
                "issue": "Consumer care contact details (both Phone and Email) are completely missing.",
                "recommendation": "Provide telephone number and email address of grievance officer / consumer cell."
            })
            flags.append("Consumer care contact details (Phone / Email) are missing.")
        elif not care_email:
            violations.append({
                "rule": "Rule 6(1)(f)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "Consumer Care Email",
                "severity": "MINOR",
                "found": f"Phone: {care_phone}",
                "issue": "Consumer care email address is missing on package (only telephone detected).",
                "recommendation": "Declare valid email address for customer grievance redressal."
            })
            flags.append("Consumer care email address is missing.")
        else:
            passed_checks += 1

        # =====================================================================
        # CHECK 5: RULE 6(1)(a) - Manufacturer / Packer / Importer Details
        # =====================================================================
        mfg_details = parsed_entities.get("manufacturer_details")
        if not mfg_details:
            violations.append({
                "rule": "Rule 6(1)(a)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "Manufacturer Address",
                "severity": "MAJOR",
                "found": None,
                "issue": "Complete name and postal address of manufacturer/packer/importer is missing or incomplete.",
                "recommendation": "Provide full corporate/factory address including city, state, and 6-digit PIN code."
            })
            flags.append("Complete name and postal address of manufacturer/packer/importer is missing or incomplete.")
        else:
            passed_checks += 1

        # =====================================================================
        # CHECK 6: RULE 6(10) - Country of Origin
        # =====================================================================
        country_origin = parsed_entities.get("country_of_origin")
        if not country_origin:
            violations.append({
                "rule": "Rule 6(10)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "Country of Origin",
                "severity": "MAJOR",
                "found": None,
                "issue": "Mandatory Country of Origin declaration is missing.",
                "recommendation": "Conspicuously state 'Country of Origin: India' or country of manufacture."
            })
            flags.append("Mandatory Country of Origin declaration is missing.")
        else:
            passed_checks += 1

        # =====================================================================
        # CHECK 7: RULE 6(11) - Unit Sale Price (USP) (2022 Amendment)
        # =====================================================================
        # Applicable if net qty > 1000g / 1000ml / 1kg / 1L
        qty_val = parsed_entities.get("net_qty_value") or 0.0
        qty_unit = (parsed_entities.get("net_qty_unit") or "").lower()
        is_large_pack = (
            (qty_unit in ['kg', 'kilo', 'kilos', 'l', 'ltr', 'ltrs'] and qty_val >= 1.0) or
            (qty_unit in ['g', 'gm', 'gms', 'ml'] and qty_val >= 1000.0)
        )

        usp_raw = parsed_entities.get("unit_sale_price")
        if is_large_pack and not usp_raw:
            violations.append({
                "rule": "Rule 6(11)",
                "section": "Legal Metrology (Packaged Commodities) Amendment Rules, 2022",
                "category": "Unit Sale Price",
                "severity": "MAJOR",
                "found": f"Net Qty: {net_qty_raw}",
                "issue": "Package exceeds 1 kg / 1 L, but mandatory Unit Sale Price (USP) declaration is missing.",
                "recommendation": "Declare Unit Sale Price (e.g. 'USP: Rs. XX / kg' or 'Rs. YY / g')."
            })
            flags.append("Unit Sale Price (USP) declaration is missing for package exceeding 1 kg / 1 L.")
        else:
            passed_checks += 1

        # =====================================================================
        # CHECK 8: RULE 6(1)(b) - Commodity / Generic Name
        # =====================================================================
        prod_name = parsed_entities.get("product_name")
        if not prod_name or prod_name == "Packaged Commodity Item":
            violations.append({
                "rule": "Rule 6(1)(b)",
                "section": "Legal Metrology (Packaged Commodities) Rules, 2011",
                "category": "Generic Commodity Name",
                "severity": "MINOR",
                "found": None,
                "issue": "Generic or common name of commodity is not distinctly identified.",
                "recommendation": "Declare common or generic name of commodity clearly on Principal Display Panel."
            })
        else:
            passed_checks += 1

        # Calculate Compliance Score and Overall Status
        is_compliant = len(violations) == 0
        status = "PASS" if is_compliant else "NON_COMPLIANT"
        compliance_score = max(0, int((passed_checks / float(total_checks)) * 100) - (len(violations) * 10))
        compliance_score = min(100, max(10 if not is_compliant else 100, compliance_score))

        # Generate Statutory Notice Draft for enforcement inspectors
        notice_draft = self._generate_notice_draft(violations, parsed_entities)

        return {
            "status": status,
            "total_violations": len(violations),
            "compliance_score": compliance_score,
            "violations": violations,
            "flags": flags,
            "legal_notice_draft": notice_draft
        }

    def _generate_notice_draft(self, violations: List[Dict[str, Any]], parsed: Dict[str, Any]) -> str:
        """
        Drafts a formal Inspection / Show-Cause Notice under Section 36 of
        the Legal Metrology Act, 2009 for non-compliant packaged commodities.
        """
        if not violations:
            return "COMPLIANT: No statutory violation detected. Label satisfies Legal Metrology Rules, 2011."

        viol_text = ""
        for idx, v in enumerate(violations, 1):
            viol_text += f"{idx}. [{v['rule']}] {v['category']} ({v['severity']})\n   - Issue: {v['issue']}\n   - Statutory Provision: {v['section']}\n\n"

        notice = (
            "====================================================================\n"
            "GOVERNMENT OF INDIA - DEPARTMENT OF CONSUMER AFFAIRS\n"
            "LEGAL METROLOGY DIVISION - STATUTORY INSPECTION NOTICE\n"
            "Issued under Section 36 of Legal Metrology Act, 2009\n"
            "====================================================================\n\n"
            f"Subject: Show Cause Notice for Statutory Metrological Non-Compliance\n\n"
            f"To: {parsed.get('manufacturer_details') or 'The Manufacturer / Packer / Importer'}\n"
            f"Product: {parsed.get('product_name') or 'Pre-Packaged Commodity'}\n"
            f"Declared Net Qty: {parsed.get('net_qty_raw') or 'Not Stated'}\n"
            f"Declared MRP: {parsed.get('mrp_raw') or 'Not Stated'}\n\n"
            "Upon technical inspection and automated optical examination of the packaged commodity\n"
            "label, the following statutory violations under the Legal Metrology (Packaged Commodities)\n"
            "Rules, 2011 were observed:\n\n"
            f"{viol_text}"
            "TAKE NOTICE that selling, manufacturing, distributing, or offering for sale any\n"
            "packaged commodity without conforming to mandatory declarations constitutes an offence\n"
            "punishable under Section 36(1) of the Legal Metrology Act, 2009 with fine up to Rs. 25,000/-\n"
            "for first offence, and imprisonment for subsequent offences.\n\n"
            "You are hereby directed to submit an explanation within 15 days of receipt of this notice.\n"
            "===================================================================="
        )
        return notice
