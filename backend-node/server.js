const express = require('express');
const cors = require('cors');
const dotenv = require('dotenv');

dotenv.config();

const authRoutes = require('./routes/auth');
const inspectRoutes = require('./routes/inspect');
const officerRoutes = require('./routes/officer');

const app = express();
const PORT = process.env.PORT || 5000;

// Enable CORS for React Frontend (Port 3000)
app.use(cors({
  origin: '*',
  allowedHeaders: ['Content-Type', 'Authorization']
}));

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// API Routes
app.use('/api/v1/auth', authRoutes);
app.use('/api/v1', inspectRoutes);
app.use('/api/v1/officer', officerRoutes);

app.get('/', (req, res) => {
  res.json({
    service: "SIH26034 Node.js Express API Gateway",
    status: "ONLINE",
    timestamp: new Date().toISOString()
  });
});

app.listen(PORT, () => {
  console.log(`====================================================`);
  console.log(`🚀 Node.js Express API Gateway running on port ${PORT}`);
  console.log(`✓ JWT Authentication & RBAC Middleware Enabled`);
  console.log(`✓ Legal Metrology Rules 2011 Validation Engine Ready`);
  console.log(`====================================================`);
});
