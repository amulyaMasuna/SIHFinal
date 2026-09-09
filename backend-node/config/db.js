const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

// -------------------------------------------------------------
// MONGODB SCHEMAS (Mongoose)
// -------------------------------------------------------------
const inspectionSchema = new mongoose.Schema({
  id: { type: String, required: true, unique: true },
  timestamp: { type: Date, default: Date.now },
  productName: { type: String, default: 'Scanned Package' },
  imageData: { type: String }, // Base64 encoded image string stored in MongoDB
  manufacturer: { type: String },
  status: { type: String, enum: ['COMPLIANT', 'NON_COMPLIANT'], required: true },
  district: { type: String, default: 'General' },
  inspectorId: { type: String, default: 'GUEST_USER' },
  inspectorEmail: { type: String, default: 'guest@client.local' },
  parsedFields: {
    mrp_raw: String,
    net_qty_raw: String,
    mfg_date_raw: String,
    consumer_care_email: String,
    consumer_care_phone: String,
    country_of_origin: String,
    manufacturer_details: String
  },
  violations: [{
    rule: String,
    severity: String,
    found: String,
    issue: String
  }],
  boundingBoxes: [{
    text: String,
    box: mongoose.Schema.Types.Mixed,
    confidence: Number
  }],
  noticeIssued: { type: Boolean, default: false }
});

const userSchema = new mongoose.Schema({
  id: { type: String, required: true, unique: true },
  name: { type: String, required: true },
  email: { type: String, required: true, unique: true },
  password: { type: String, required: true },
  role: { type: String, enum: ['CONSUMER', 'LEGAL_METROLOGY_OFFICER'], default: 'CONSUMER' },
  accountStatus: { type: String, default: 'ACTIVE' },
  employeeId: String,
  district: { type: String, default: 'Pune' }
});

const InspectionModel = mongoose.model('Inspection', inspectionSchema);
const UserModel = mongoose.model('User', userSchema);

// In-Memory Fallback Data Store
const memoryDb = {
  users: [],
  inspections: [],
  notices: [],
  isMongoConnected: false
};

// Seed initial fallback data
async function seedInitialData() {
  const hashedPassword = await bcrypt.hash('password123', 10);
  memoryDb.users = [
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
}

// Connect to MongoDB if MONGODB_URI is configured
const MONGODB_URI = process.env.MONGODB_URI;
if (MONGODB_URI) {
  mongoose.connect(MONGODB_URI, { useNewUrlParser: true, useUnifiedTopology: true })
    .then(() => {
      memoryDb.isMongoConnected = true;
      console.log('✓ Successfully connected to MongoDB database!');
    })
    .catch((err) => {
      console.log(`MongoDB connection notice (${err.message}). Operating with in-memory DB fallback.`);
    });
} else {
  console.log('ℹ MONGODB_URI not provided. Operating with high-performance in-memory database store.');
}

seedInitialData();

module.exports = {
  db: memoryDb,
  InspectionModel,
  UserModel
};
