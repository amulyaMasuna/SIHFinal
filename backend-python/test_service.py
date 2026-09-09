"""
Comprehensive Test Suite for Legal Metrology AI Microservice
============================================================
Tests:
1. Regex & NLP Semantic Entity Extraction
2. Legal Metrology Rules 2011 Statutory Validation Engine
3. Rule 6(1)(e): MRP and tax syntax (inclusive vs Taxes Extra)
4. Rule 13: Standard SI units vs illegal units ('gms', 'gm', 'kilos', 'ltrs', 'ml.')
5. Rule 11: Qualifying words prohibition ('approximate', 'when packed')
6. Rule 6(1)(d): Month & Year of Manufacture/Packing
7. Rule 6(1)(f): Consumer Care grievance redressal contact (Email + Telephone)
8. Rule 6(1)(a): Manufacturer/Packer full postal address and PIN code
9. Rule 6(10): Country of Origin declaration
10. Rule 6(11): Unit Sale Price (USP) for large commodities (> 1kg / 1L)
11. Statutory Show-Cause Notice Generation under Section 36 of Legal Metrology Act, 2009
"""

import os
import sys
import unittest

# Ensure services package is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.nlp_parser import NLPParser
from services.rule_validator import LegalMetrologyValidator


class TestNLPParser(unittest.TestCase):
    def setUp(self):
        self.parser = NLPParser()

    def test_compliant_label_parsing(self):
        sample_lines = [
            "PREMIUM ASSAM TEA",
            "MRP Rs. 249.00 (inclusive of all taxes)",
            "Net Qty: 500 g",
            "Mfg Date: 03/2026",
            "Best Before 12 Months from Packaging",
            "Manufactured by: Tata Consumer Products Ltd, Pune Industrial Area, Pune 411001",
            "Consumer Care Cell: Email: care@tataconsumer.com, Tel: 1800-108-4488",
            "Country of Origin: India",
            "Batch No: TATA26A"
        ]
        full_text = "\n".join(sample_lines)

        parsed = self.parser.parse(sample_lines, full_text)

        self.assertEqual(parsed["mrp_value"], 249.0)
        self.assertTrue(parsed["tax_inclusive"])
        self.assertFalse(parsed["tax_extra_detected"])
        self.assertEqual(parsed["net_qty_value"], 500.0)
        self.assertEqual(parsed["net_qty_unit"], "g")
        self.assertFalse(parsed["is_non_standard_unit"])
        self.assertIn("03/2026", parsed["mfg_date_raw"])
        self.assertEqual(parsed["consumer_care_email"], "care@tataconsumer.com")
        self.assertIn("1800-108-4488", parsed["consumer_care_phone"])
        self.assertIn("Tata Consumer Products", parsed["manufacturer_details"])
        self.assertIn("411001", parsed["manufacturer_details"])
        self.assertIn("India", parsed["country_of_origin"])
        self.assertEqual(parsed["batch_number"], "TATA26A")

    def test_non_standard_units_and_taxes_extra(self):
        sample_lines = [
            "CRUNCHY COOKIES",
            "MRP Rs. 150 Taxes Extra",
            "Net Wt: 250 gms",  # Prohibited unit under Rule 13
            "Manufactured by: Local Bakery Works",
            "Country of Origin: India"
        ]
        full_text = "\n".join(sample_lines)

        parsed = self.parser.parse(sample_lines, full_text)

        self.assertEqual(parsed["mrp_value"], 150.0)
        self.assertTrue(parsed["tax_extra_detected"])
        self.assertTrue(parsed["is_non_standard_unit"])
        self.assertEqual(parsed["non_standard_unit_found"], "gms")
        self.assertIsNone(parsed["consumer_care_email"])
        self.assertIsNone(parsed["consumer_care_phone"])
        self.assertIsNone(parsed["mfg_date_raw"])

    def test_qualifying_words_prohibited(self):
        sample_lines = [
            "PURE HONEY",
            "MRP Rs. 350 (incl. of all taxes)",
            "Net Weight approx 500 g",  # Prohibited under Rule 11
            "Mfg Date: 01/2026",
            "Manufactured by: Honey Corp, Jaipur 302001",
            "Consumer Care: Email: care@honey.in, Tel: 1800-111-2222",
            "Country of Origin: India"
        ]
        full_text = "\n".join(sample_lines)
        parsed = self.parser.parse(sample_lines, full_text)
        self.assertTrue(parsed["has_qualifying_words"])


class TestLegalMetrologyValidator(unittest.TestCase):
    def setUp(self):
        self.parser = NLPParser()
        self.validator = LegalMetrologyValidator()

    def test_compliant_package_audit(self):
        sample_lines = [
            "PREMIUM ASSAM TEA",
            "MRP Rs. 249.00 (inclusive of all taxes)",
            "Net Qty: 500 g",
            "Mfg Date: 03/2026",
            "Best Before 12 Months from Packaging",
            "Manufactured by: Tata Consumer Products Ltd, Pune Industrial Area, Pune 411001",
            "Consumer Care: Email: care@tataconsumer.com, Tel: 1800-108-4488",
            "Country of Origin: India",
            "Batch No: TATA26A"
        ]
        full_text = "\n".join(sample_lines)
        parsed = self.parser.parse(sample_lines, full_text)

        audit = self.validator.validate(parsed, full_text)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["total_violations"], 0)
        self.assertEqual(audit["compliance_score"], 100)
        self.assertIn("COMPLIANT", audit["legal_notice_draft"])

    def test_violations_detected(self):
        sample_lines = [
            "MRP Rs. 150 Taxes Extra",
            "Net Qty: 500 gms",  # Violation: Rule 13
            # Missing Mfg Date: Rule 6(1)(d)
            # Missing Consumer Care: Rule 6(1)(f)
            # Missing Manufacturer: Rule 6(1)(a)
            # Missing Country of Origin: Rule 6(10)
        ]
        full_text = "\n".join(sample_lines)
        parsed = self.parser.parse(sample_lines, full_text)

        audit = self.validator.validate(parsed, full_text)

        self.assertEqual(audit["status"], "NON_COMPLIANT")
        self.assertGreater(audit["total_violations"], 0)

        rules_violated = [v["rule"] for v in audit["violations"]]
        self.assertIn("Rule 6(1)(e)", rules_violated)  # Taxes extra / syntax
        self.assertIn("Rule 13", rules_violated)        # Non-standard unit 'gms'
        self.assertIn("Rule 6(1)(d)", rules_violated)  # Missing mfg date
        self.assertIn("Rule 6(1)(f)", rules_violated)  # Missing consumer care
        self.assertIn("Rule 6(1)(a)", rules_violated)  # Missing manufacturer

        # Check notice generation
        self.assertIn("Section 36 of Legal Metrology Act, 2009", audit["legal_notice_draft"])
        self.assertIn("Show Cause Notice", audit["legal_notice_draft"])

    def test_unit_sale_price_rule_for_large_pack(self):
        # Rule 6(11): Large pack (> 1 kg / 1 L) requires Unit Sale Price (USP)
        sample_lines = [
            "WHEAT FLOUR CHAKKI ATTA",
            "MRP Rs. 450.00 (inclusive of all taxes)",
            "Net Qty: 5 kg",  # Large pack > 1 kg, no USP specified
            "Mfg Date: 02/2026",
            "Manufactured by: Mega Flour Mills Ltd, Industrial Zone, Mumbai 400001",
            "Consumer Care: Email: help@flourmills.com, Tel: 1800-222-3333",
            "Country of Origin: India"
        ]
        full_text = "\n".join(sample_lines)
        parsed = self.parser.parse(sample_lines, full_text)

        audit = self.validator.validate(parsed, full_text)

        rules_violated = [v["rule"] for v in audit["violations"]]
        self.assertIn("Rule 6(11)", rules_violated)

    def test_various_illegal_unit_symbols(self):
        illegal_samples = ["1 ltr", "500 ml.", "2 kilos", "100 gm", "5 ltrs"]
        for sample in illegal_samples:
            lines = [f"Net Qty: {sample}"]
            parsed = self.parser.parse(lines, "\n".join(lines))
            audit = self.validator.validate(parsed, "\n".join(lines))
            rules_violated = [v["rule"] for v in audit["violations"]]
            self.assertIn("Rule 13", rules_violated, f"Failed to flag illegal symbol in '{sample}'")

    def test_qualifying_words_violation(self):
        lines = [
            "MRP Rs. 100 (incl. of all taxes)",
            "Net Qty: approx 500 g",  # Prohibited qualifying word under Rule 11
            "Mfg Date: 01/2026",
            "Manufactured by: Test Mills, Delhi 110001",
            "Consumer Care: Email: test@mills.com, Tel: 1800-123-4567",
            "Country of Origin: India"
        ]
        full_text = "\n".join(lines)
        parsed = self.parser.parse(lines, full_text)
        audit = self.validator.validate(parsed, full_text)
        rules_violated = [v["rule"] for v in audit["violations"]]
        self.assertIn("Rule 11", rules_violated)


class TestOCREngine(unittest.TestCase):
    def test_box_sorting_reading_order(self):
        from services.ocr_engine import OCREngine
        engine = OCREngine(use_gpu=False)

        # Unordered boxes on different lines
        unordered_boxes = [
            {"box": [[200, 100], [300, 100], [300, 120], [200, 120]], "text": "World"},
            {"box": [[50, 10], [150, 10], [150, 30], [50, 30]], "text": "Top Line"},
            {"box": [[50, 100], [180, 100], [180, 120], [50, 120]], "text": "Hello"}
        ]

        sorted_boxes = engine._sort_boxes_reading_order(unordered_boxes)
        sorted_texts = [b["text"] for b in sorted_boxes]
        
        # Expected reading order: "Top Line", then "Hello", then "World"
        self.assertEqual(sorted_texts, ["Top Line", "Hello", "World"])

    def test_dynamic_image_extraction(self):
        import cv2
        import numpy as np
        from services.ocr_engine import OCREngine

        engine = OCREngine(use_gpu=False)
        img = np.ones((150, 500, 3), dtype=np.uint8) * 255
        cv2.putText(img, 'MRP Rs. 249.00', (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
        cv2.putText(img, 'Net Qty: 500 g', (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        result = engine.extract_text(img)

        self.assertIn("raw_text_lines", result)
        self.assertIn("bounding_boxes", result)
        self.assertGreater(len(result["raw_text_lines"]), 0)
        self.assertTrue(any("249" in line for line in result["raw_text_lines"]))


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNLPParser)
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestLegalMetrologyValidator))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestOCREngine))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
