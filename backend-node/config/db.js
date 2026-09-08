// In-Memory Data Store + MongoDB Connector for SIH26034
const bcrypt = require('bcryptjs');

// Mock In-Memory Store
const db = {
  users: [],
  inspections: [],
  notices: []
};

// Seed Initial Pre-approved Users & Officers
async function seedInitialData() {
  const hashedPassword = await bcrypt.hash('password123', 10);
  
  db.users = [
    {
      id: 'usr_001',
      name: 'Priya Sharma (Consumer)',
      email: 'consumer@example.com',
      password: hashedPassword,
      role: 'CONSUMER',
      accountStatus: 'ACTIVE',
      district: 'Pune'
    },
    {
      id: 'usr_002',
      name: 'Rajesh Kumar (Field Officer)',
      email: 'field.officer@example.com',
      password: hashedPassword,
      role: 'CONSUMER',
      accountStatus: 'ACTIVE',
      district: 'Mumbai'
    },
    {
      id: 'usr_003',
      name: 'Dr. V. K. Patil (Legal Metrology Officer)',
      email: 'lmo.patil@nic.in',
      password: hashedPassword,
      role: 'LEGAL_METROLOGY_OFFICER',
      accountStatus: 'ACTIVE',
      employeeId: 'LMO-MH-2024-88',
      district: 'Pune'
    }
  ];

  // Seed sample flagged non-compliant cases
  db.inspections = [
    {
      id: 'INSP-2026-901',
      timestamp: new Date().toISOString(),
      productName: 'Crunchy Potato Chips 100g',
      manufacturer: 'Bites Snacks India Pvt Ltd, MIDC Area, Pune',
      status: 'NON_COMPLIANT',
      district: 'Pune',
      inspectorId: 'usr_001',
      inspectorEmail: 'consumer@example.com',
      parsedFields: {
        mrp_raw: 'MRP Rs. 50.00',
        net_qty_raw: 'Net Wt: 100 gms',
        mfg_date_raw: 'MFG 04/2026',
        consumer_care_email: 'care@bitessnacks.in'
      },
      violations: [
        {
          rule: 'Rule 13 (Standard Units)',
          severity: 'MAJOR',
          found: 'Net Wt: 100 gms',
          issue: "Illegal unit symbol 'gms' detected. Mandated standard symbol under Legal Metrology Rules 2011 is 'g'."
        },
        {
          rule: 'Rule 6(1)(e) (MRP Tax Statement)',
          severity: 'MAJOR',
          found: 'MRP Rs. 50.00',
          issue: "MRP declaration does not state 'inclusive of all taxes'."
        }
      ],
      noticeIssued: false
    }
  ];
  
  console.log('✓ Database & Seed Data Initialized (Pre-loaded 3 Users & 1 Flagged Case)');
}

seedInitialData();

module.exports = db;
