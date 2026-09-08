const PDFDocument = require('pdfkit');

/**
 * Generates an official Statutory Show Cause Notice PDF under Section 36 of Legal Metrology Act, 2009
 */
function generateLegalNoticePDF(inspectionRecord, officerDetails) {
  return new Promise((resolve, reject) => {
    try {
      const doc = new PDFDocument({ margin: 50 });
      const buffers = [];

      doc.on('data', buffers.push.bind(buffers));
      doc.on('end', () => {
        const pdfData = Buffer.concat(buffers);
        resolve(pdfData);
      });

      // --- PDF HEADER ---
      doc.fillColor('#1e3a8a')
         .fontSize(16)
         .text('GOVERNMENT OF INDIA', { align: 'center' })
         .fontSize(14)
         .text('DEPARTMENT OF LEGAL METROLOGY', { align: 'center' })
         .fontSize(10)
         .fillColor('#4b5563')
         .text('MINISTRY OF CONSUMER AFFAIRS, FOOD & PUBLIC DISTRIBUTION', { align: 'center' })
         .moveDown(1.5);

      // Horizontal Divider Line
      doc.moveTo(50, doc.y).lineTo(550, doc.y).strokeColor('#1e3a8a').lineWidth(2).stroke().moveDown(1);

      // --- NOTICE TITLE & ID ---
      const noticeId = `LMN-${Date.now().toString().slice(-6)}`;
      doc.fillColor('#991b1b')
         .fontSize(14)
         .text('STATUTORY SHOW CAUSE NOTICE', { align: 'center' })
         .fontSize(10)
         .fillColor('#111827')
         .text(`Notice Reference No: ${noticeId}`, { align: 'center' })
         .text(`Date of Issuance: ${new Date().toLocaleDateString('en-IN')}`, { align: 'center' })
         .moveDown(1.5);

      // --- RECIPIENT & SUBJECT ---
      doc.fontSize(10)
         .text(`TO:`, { weight: 'bold' })
         .text(`The Managing Director / Authorized Signatory`)
         .text(`${inspectionRecord.manufacturer || 'Non-Compliant Manufacturer / Packer Entity'}`)
         .moveDown(1);

      doc.text(`SUBJECT: Notice for Non-Compliance under Section 36 of Legal Metrology Act, 2009 read with Legal Metrology (Packaged Commodities) Rules, 2011.`, { underline: true })
         .moveDown(1);

      // --- BODY TEXT ---
      doc.text(`WHEREAS, during automated digital compliance inspection conducted under assigned jurisdiction (${inspectionRecord.district || 'General'}), the packaged commodity detailed below was scanned and analyzed by the AI Legal Metrology Verification System:`)
         .moveDown(0.8);

      // Product Details Table
      doc.fillColor('#1e293b')
         .text(`• Product Identifier / Name: ${inspectionRecord.productName || 'Scanned Packaged Commodity'}`)
         .text(`• Inspection Log Reference: ${inspectionRecord.id}`)
         .text(`• Scanned Timestamp: ${new Date(inspectionRecord.timestamp).toLocaleString('en-IN')}`)
         .moveDown(1);

      // --- VIOLATIONS SECTION ---
      doc.fillColor('#991b1b').fontSize(11).text('SUMMARY OF STATUTORY VIOLATIONS DETECTED:', { underline: true }).moveDown(0.5);

      doc.fillColor('#111827').fontSize(9);
      if (inspectionRecord.violations && inspectionRecord.violations.length > 0) {
        inspectionRecord.violations.forEach((v, index) => {
          doc.text(`${index + 1}. [${v.rule}] - ${v.category || 'Compliance Defect'}`);
          doc.text(`   Found: "${v.found || 'Non-compliant entry'}"`);
          doc.text(`   Violation: ${v.issue}`);
          doc.moveDown(0.5);
        });
      } else {
        doc.text(`1. Non-compliance detected in mandatory package declarations.`);
      }

      doc.moveDown(1);

      // --- LEGAL REQUIREMENT & PENALTY DIRECTIVE ---
      doc.fontSize(10).fillColor('#111827')
         .text(`NOW THEREFORE, in exercise of powers conferred under Section 36 of the Legal Metrology Act, 2009, you are hereby directed to SHOW CAUSE within 15 (Fifteen) days of receipt of this notice as to why legal proceedings under Section 36 / 39 should not be initiated against your enterprise.`)
         .moveDown(1)
         .text(`Failure to submit a valid compliance response within the stipulated time frame shall result in ex-parte legal enforcement and compounding proceedings as per law.`)
         .moveDown(2);

      // --- SIGNATURE BLOCK ---
      doc.text(`Issued By:`, { align: 'right' })
         .text(`${officerDetails.name || 'Legal Metrology Officer'}`, { align: 'right', weight: 'bold' })
         .text(`Designation: ${officerDetails.role || 'Legal Metrology Officer'}`, { align: 'right' })
         .text(`Employee ID: ${officerDetails.employeeId || 'LMO-GOI-INSPEC'}`, { align: 'right' })
         .text(`Jurisdiction: ${officerDetails.district || 'Revenue Division'}`, { align: 'right' });

      doc.end();
    } catch (err) {
      reject(err);
    }
  });
}

module.exports = { generateLegalNoticePDF };
