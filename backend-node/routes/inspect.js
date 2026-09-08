const express = require('express');
const router = express.Router();
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const db = require('../config/db');
const { optionalToken } = require('../middleware/authMiddleware');
const { validateLegalMetrologyRules } = require('../services/ruleEngine');

const upload = multer({ storage: multer.memoryStorage() });
const PYTHON_AI_URL = process.env.PYTHON_AI_URL || 'http://localhost:8000/api/v1/extract';

// CORE INSPECTION ENDPOINT: POST /api/v1/inspect
router.post('/inspect', optionalToken, upload.single('image'), async (req, res) => {
  try {
    let aiResponseData = null;

    if (req.file) {
      // 1. Package image buffer into FormData to send to Python AI Microservice
      const formData = new FormData();
      formData.append('file', req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype
      });

      try {
        const pyRes = await axios.post(PYTHON_AI_URL, formData, {
          headers: formData.getHeaders(),
          timeout: 10000
        });
        aiResponseData = pyRes.data;
      } catch (pyErr) {
        console.log(`Python AI Microservice unavailable (${pyErr.message}). Using simulated extraction engine.`);
      }
    }

    // Fallback Simulated Data if Python microservice is offline
    if (!aiResponseData) {
      aiResponseData = {
        ocr_engine_used: "SIMULATED_DEMO_ENGINE",
        raw_text_lines: [
          "M.R.P. Rs. 150.00",
          "Net Qty: 500 gms",
          "Mfg Date: 05/2026",
          "Mfd by: Apex Consumer Goods Pvt Ltd, MIDC Pune 411018",
          "Customer Care: care@apexgoods.com | Tel: 18002001234"
        ],
        parsed_entities: {
          mrp_raw: "M.R.P. Rs. 150.00",
          net_qty_raw: "Net Qty: 500 gms",
          mfg_date_raw: "Mfg Date: 05/2026",
          consumer_care_email: "care@apexgoods.com",
          consumer_care_phone: "18002001234",
          country_of_origin: "India",
          manufacturer_details: "Mfd by: Apex Consumer Goods Pvt Ltd, MIDC Pune 411018"
        },
        bounding_boxes: [
          { text: "M.R.P. Rs. 150.00", box: [[100, 150], [450, 150], [450, 185], [100, 185]], confidence: 0.95 },
          { text: "Net Qty: 500 gms", box: [[100, 200], [320, 200], [320, 230], [100, 230]], confidence: 0.91 },
          { text: "Mfg Date: 05/2026", box: [[100, 245], [300, 245], [300, 275], [100, 275]], confidence: 0.96 },
          { text: "Apex Consumer Goods", box: [[100, 290], [550, 290], [550, 320], [100, 320]], confidence: 0.89 }
        ]
      };
    }

    const parsed = aiResponseData.parsed_entities;
    const fullText = (aiResponseData.raw_text_lines || []).join(' ');

    // 2. Execute Legal Metrology (Packaged Commodities) Rules, 2011 Validation Engine
    const ruleEvaluation = validateLegalMetrologyRules(parsed, fullText);

    // 3. Create Inspection Log Record
    const inspectionLog = {
      id: `INSP-${Date.now().toString().slice(-6)}`,
      timestamp: new Date().toISOString(),
      productName: req.body.productName || 'Scanned Package Item',
      manufacturer: parsed.manufacturer_details || 'Apex Consumer Goods Pvt Ltd, Pune',
      status: ruleEvaluation.status,
      district: req.user ? req.user.district : 'Pune',
      inspectorId: req.user ? req.user.userId : 'GUEST_USER',
      inspectorEmail: req.user ? req.user.email : 'guest@client.local',
      parsedFields: parsed,
      violations: ruleEvaluation.violations,
      boundingBoxes: aiResponseData.bounding_boxes,
      noticeIssued: false
    };

    // Save to Database
    db.inspections.unshift(inspectionLog);

    // 4. Return Full Response to React Frontend
    res.json({
      success: true,
      inspectionId: inspectionLog.id,
      status: ruleEvaluation.status,
      total_violations: ruleEvaluation.total_violations,
      violations: ruleEvaluation.violations,
      parsed_entities: parsed,
      bounding_boxes: aiResponseData.bounding_boxes,
      ocr_engine_used: aiResponseData.ocr_engine_used
    });

  } catch (error) {
    console.error('Inspection Route Error:', error);
    res.status(500).json({ error: 'Inspection processing failed: ' + error.message });
  }
});

// GET USER'S INSPECTION HISTORY
router.get('/history', optionalToken, (req, res) => {
  const userEmail = req.user ? req.user.email : 'guest@client.local';
  const history = db.inspections.filter(i => i.inspectorEmail === userEmail || i.inspectorId === 'GUEST_USER');
  res.json({ history });
});

module.exports = router;
