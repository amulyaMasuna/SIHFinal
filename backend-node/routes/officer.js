const express = require('express');
const router = express.Router();
const { db, InspectionModel } = require('../config/db');
const { authenticateToken, requireRole } = require('../middleware/authMiddleware');
const { generateLegalNoticePDF } = require('../services/pdfGenerator');
const { dispatchLegalNoticeEmail } = require('../services/emailService');

// Protect all officer routes with JWT + LEGAL_METROLOGY_OFFICER role check
router.use(authenticateToken);
router.use(requireRole('LEGAL_METROLOGY_OFFICER'));

// 1. GET FLAGGED CASES QUEUE
router.get('/flagged-cases', async (req, res) => {
  const officerDistrict = req.user.district || 'Pune';
  let flaggedCases = [];

  if (db.isMongoConnected) {
    flaggedCases = await InspectionModel.find({ status: 'NON_COMPLIANT' }).sort({ timestamp: -1 });
  } else {
    flaggedCases = db.inspections.filter(i => 
      i.status === 'NON_COMPLIANT' && 
      (i.district === officerDistrict || officerDistrict === 'General' || i.district === 'Pune')
    );
  }

  res.json({
    success: true,
    officer: req.user.email,
    district: officerDistrict,
    totalFlagged: flaggedCases.length,
    cases: flaggedCases
  });
});

// 2. GENERATE LEGAL SHOW CAUSE NOTICE PDF (Section 36)
router.get('/notice-pdf/:inspectionId', async (req, res) => {
  const { inspectionId } = req.params;
  let inspection = null;

  if (db.isMongoConnected) {
    inspection = await InspectionModel.findOne({ id: inspectionId });
  }
  if (!inspection) {
    inspection = db.inspections.find(i => i.id === inspectionId);
  }

  if (!inspection) {
    return res.status(404).json({ error: 'Inspection record not found.' });
  }

  try {
    const pdfBuffer = await generateLegalNoticePDF(inspection, req.user);
    
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename=Legal_Notice_${inspectionId}.pdf`);
    res.send(pdfBuffer);
  } catch (error) {
    res.status(500).json({ error: 'PDF generation failed: ' + error.message });
  }
});

// 3. AUTOMATED LEGAL NOTICE ISSUANCE TO MANUFACTURERS
router.post('/issue-notice/:inspectionId', async (req, res) => {
  const { inspectionId } = req.params;
  let inspection = null;

  if (db.isMongoConnected) {
    inspection = await InspectionModel.findOne({ id: inspectionId });
  }
  if (!inspection) {
    inspection = db.inspections.find(i => i.id === inspectionId);
  }

  if (!inspection) {
    return res.status(404).json({ error: 'Inspection record not found.' });
  }

  try {
    const pdfBuffer = await generateLegalNoticePDF(inspection, req.user);
    const mfrEmail = (inspection.parsedFields && inspection.parsedFields.consumer_care_email) || 'legal@manufacturer.in';
    
    await dispatchLegalNoticeEmail(mfrEmail, inspectionId, pdfBuffer);

    // Update status in DB
    inspection.noticeIssued = true;
    inspection.noticeIssuedAt = new Date().toISOString();
    inspection.noticeIssuedBy = req.user.email;

    if (db.isMongoConnected) {
      await InspectionModel.updateOne({ id: inspectionId }, { 
        noticeIssued: true,
        noticeIssuedAt: inspection.noticeIssuedAt,
        noticeIssuedBy: req.user.email
      });
    }

    res.json({
      success: true,
      message: `Statutory Legal Notice ${inspectionId} auto-dispatched to manufacturer (${mfrEmail}).`,
      noticeDetails: {
        inspectionId,
        dispatchedTo: mfrEmail,
        issuedBy: req.user.email,
        timestamp: inspection.noticeIssuedAt
      }
    });

  } catch (error) {
    res.status(500).json({ error: 'Notice issuance failed: ' + error.message });
  }
});

module.exports = router;
