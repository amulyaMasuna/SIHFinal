const express = require('express');
const router = express.Router();
const multer = require('multer');
const axios = require('axios');
const FormData = require('form-data');
const { db, InspectionModel } = require('../config/db');
const { optionalToken } = require('../middleware/authMiddleware');
const { validateLegalMetrologyRules } = require('../services/ruleEngine');

const upload = multer({ storage: multer.memoryStorage() });
const PYTHON_AI_URL = process.env.PYTHON_AI_URL || 'http://localhost:8000/api/v1/extract';

// CORE INSPECTION ENDPOINT: POST /api/v1/inspect
router.post('/inspect', optionalToken, upload.single('image'), async (req, res) => {
  try {
    let aiResponseData = null;
    let imageBase64 = null;

    if (req.file) {
      imageBase64 = `data:${req.file.mimetype};base64,${req.file.buffer.toString('base64')}`;

      // 1. Package image buffer into FormData to send to Python AI Microservice
      const formData = new FormData();
      formData.append('file', req.file.buffer, {
        filename: req.file.originalname,
        contentType: req.file.mimetype
      });

      try {
        console.log(`📡 Sending image to Python AI service: ${PYTHON_AI_URL}`);
        const pyRes = await axios.post(PYTHON_AI_URL, formData, {
          headers: formData.getHeaders(),
          timeout: 45000
        });
        aiResponseData = pyRes.data;
        console.log('✓ Received response from Python AI Microservice!');
      } catch (pyErr) {
        console.log(`Python AI Microservice notice (${pyErr.message}). Using fallback processing.`);
      }
    }

    // Fallback Simulated Data if Python microservice is offline
    if (!aiResponseData) {
      aiResponseData = {
        ocr_engine_used: "SIMULATED_DEMO_ENGINE",
        raw_text_lines: [
          "Rajkamal's NAMKEEN",
          "DIET NAVRATAN MIX (200 g)",
          "Net Wt : 200 g",
          "Pkdt : 05-09-16",
          "MRP IN MUMBAI Rs. 70/-",
          "(Incl of All Taxes):",
          "Manufactured & Packed By: RAJKAMAL NAMKEENS PVT.LTD.",
          "Email: rajkamalnamkeens@gmail.com | Tel: +91-22-25782103"
        ],
        parsed_entities: {
          mrp_raw: "MRP Rs. 70",
          net_qty_raw: "200 g",
          mfg_date_raw: "05-09-16",
          consumer_care_email: "rajkamalnamkeens@gmail.com",
          consumer_care_phone: "+91-22-25782103",
          country_of_origin: "India",
          manufacturer_details: "RAJKAMAL NAMKEENS PVT.LTD., Mumbai"
        },
        bounding_boxes: [
          { text: "DIET NAVRATAN MIX (200 g)", box: [[100, 150], [450, 150], [450, 185], [100, 185]], confidence: 0.95 },
          { text: "Net Wt : 200 g", box: [[100, 200], [320, 200], [320, 230], [100, 230]], confidence: 0.96 },
          { text: "Pkdt : 05-09-16", box: [[100, 245], [300, 245], [300, 275], [100, 275]], confidence: 0.95 },
          { text: "RAJKAMAL NAMKEENS PVT.LTD.", box: [[100, 290], [550, 290], [550, 320], [100, 320]], confidence: 0.93 }
        ]
      };
    }

    const parsed = aiResponseData.parsed_entities || {};
    const fullText = (aiResponseData.raw_text_lines || []).join(' ');

    // 2. Execute Legal Metrology (Packaged Commodities) Rules, 2011 Validation Engine
    const ruleEvaluation = validateLegalMetrologyRules(parsed, fullText);

    // Merge Python statutory flags if present
    if (aiResponseData.compliance_audit && aiResponseData.compliance_audit.flags) {
      aiResponseData.compliance_audit.flags.forEach(flag => {
        if (!ruleEvaluation.violations.some(v => v.issue && v.issue.includes(flag))) {
          ruleEvaluation.violations.push({
            rule: 'Statutory Metrology Check',
            severity: 'MAJOR',
            issue: flag
          });
        }
      });
      ruleEvaluation.total_violations = ruleEvaluation.violations.length;
      if (ruleEvaluation.total_violations > 0) {
        ruleEvaluation.status = 'NON_COMPLIANT';
      }
    }

    // 3. Create Inspection Log Record
    const inspectionLog = {
      id: `INSP-${Date.now().toString().slice(-6)}`,
      timestamp: new Date().toISOString(),
      productName: req.body.productName || (parsed.manufacturer_details ? 'Rajkamal Diet Navratan Mix' : 'Scanned Package Item'),
      imageData: imageBase64,
      manufacturer: parsed.manufacturer_details || 'RAJKAMAL NAMKEENS PVT.LTD., Mumbai',
      status: ruleEvaluation.status,
      district: req.user ? req.user.district : 'Pune',
      inspectorId: req.user ? req.user.userId : 'GUEST_USER',
      inspectorEmail: req.user ? req.user.email : 'guest@client.local',
      parsedFields: parsed,
      violations: ruleEvaluation.violations,
      boundingBoxes: aiResponseData.bounding_boxes,
      extracted_fields: aiResponseData.extracted_fields,
      noticeIssued: false
    };

    // Save to Database
    if (db.isMongoConnected) {
      await InspectionModel.create(inspectionLog);
      console.log(`✓ Inspection ${inspectionLog.id} saved to MongoDB!`);
    }
    db.inspections.unshift(inspectionLog);

    // 4. Return Full Response to React Frontend
    res.json({
      success: true,
      inspectionId: inspectionLog.id,
      status: ruleEvaluation.status,
      total_violations: ruleEvaluation.total_violations,
      violations: ruleEvaluation.violations,
      parsed_entities: parsed,
      extracted_fields: aiResponseData.extracted_fields,
      bounding_boxes: aiResponseData.bounding_boxes,
      ocr_engine_used: aiResponseData.ocr_engine_used
    });

  } catch (error) {
    console.error('Inspection Route Error:', error);
    res.status(500).json({ error: 'Inspection processing failed: ' + error.message });
  }
});

// GET USER'S INSPECTION HISTORY
router.get('/history', optionalToken, async (req, res) => {
  try {
    const userEmail = req.user ? req.user.email : 'guest@client.local';
    let history = [];
    
    if (db.isMongoConnected) {
      history = await InspectionModel.find({ inspectorEmail: userEmail }).sort({ timestamp: -1 });
    } else {
      history = db.inspections.filter(i => i.inspectorEmail === userEmail || i.inspectorId === 'GUEST_USER');
    }
    res.json({ history });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
