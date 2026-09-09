const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config();

const authRoutes = require('./routes/auth');
const inspectRoutes = require('./routes/inspect');
const officerRoutes = require('./routes/officer');

const app = express();
const PORT = process.env.PORT || 5000;

// Enable universal CORS for all origins, methods, and preflight requests
app.use(cors());
app.options('*', cors());

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// Root health check endpoint
app.get('/', (req, res) => {
  res.json({
    service: "SIH26034 Node.js Express API Gateway",
    status: "ONLINE",
    timestamp: new Date().toISOString()
  });
});

app.get('/healthz', (req, res) => {
  res.status(200).send('OK');
});

// API Routes
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1', inspectRoutes);
app.use('/api/v1/officer', officerRoutes);

// Explicit 0.0.0.0 binding for Render proxy environment
app.listen(PORT, '0.0.0.0', () => {
  console.log(`====================================================`);
  console.log(`🚀 Node.js Express API Gateway running on 0.0.0.0:${PORT}`);
  console.log(`✓ Universal CORS & Preflight Enabled`);
  console.log(`✓ JWT Authentication & RBAC Middleware Active`);
  console.log(`✓ Legal Metrology Rules 2011 Validation Engine Ready`);
  console.log(`====================================================`);
});
