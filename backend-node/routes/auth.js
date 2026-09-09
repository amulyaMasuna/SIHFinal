const express = require('express');
const router = express.Router();
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');
const { db, UserModel } = require('../config/db');
const { JWT_SECRET } = require('../middleware/authMiddleware');
const { sendVerificationOTP } = require('../services/emailService');

// 1. REGISTER USER / OFFICER
router.post('/register', async (req, res) => {
  try {
    const { name, email, password, role, employeeId, district } = req.body;

    if (!email || !password || !name) {
      return res.status(400).json({ error: 'Name, email, and password are required.' });
    }

    // Check if user already exists in MongoDB or In-Memory DB
    let existingUser = null;
    if (db.isMongoConnected) {
      existingUser = await UserModel.findOne({ email: email.toLowerCase() });
    } else {
      existingUser = db.users.find(u => u.email.toLowerCase() === email.toLowerCase());
    }

    if (existingUser) {
      return res.status(400).json({ error: 'User with this email already exists.' });
    }

    let userRole = role === 'LEGAL_METROLOGY_OFFICER' ? 'LEGAL_METROLOGY_OFFICER' : 'CONSUMER';
    let accountStatus = 'ACTIVE';

    // Government Domain & Verification Logic for Officer Role
    if (userRole === 'LEGAL_METROLOGY_OFFICER') {
      const isGovEmail = email.endsWith('.gov.in') || email.endsWith('.nic.in');
      if (!isGovEmail) {
        return res.status(400).json({
          error: "Official Registration Error: Legal Metrology Officer accounts require an official government email (.gov.in or .nic.in)."
        });
      }
      accountStatus = 'ACTIVE'; // Auto-activate for demo mode
    }

    const hashedPassword = await bcrypt.hash(password, 10);
    const otpCode = Math.floor(100000 + Math.random() * 900000).toString();

    const newUser = {
      id: `usr_${Date.now()}`,
      name,
      email: email.toLowerCase(),
      password: hashedPassword,
      role: userRole,
      accountStatus,
      employeeId: employeeId || (userRole === 'LEGAL_METROLOGY_OFFICER' ? 'LMO-IND-2026' : null),
      district: district || 'General',
      verificationOTP: otpCode
    };

    if (db.isMongoConnected) {
      await UserModel.create(newUser);
      console.log(`✓ User ${newUser.email} created in MongoDB!`);
    }
    db.users.push(newUser);

    // Trigger Nodemailer Real Email Verification
    try {
      sendVerificationOTP(email, otpCode);
    } catch (e) {
      console.log(`Email verification notice: ${e.message}`);
    }

    res.status(201).json({
      success: true,
      message: 'Account registered successfully!',
      user: { id: newUser.id, name: newUser.name, email: newUser.email, role: newUser.role, status: newUser.accountStatus }
    });

  } catch (error) {
    console.error('Register Route Error:', error);
    res.status(500).json({ error: 'Registration failed: ' + error.message });
  }
});

// 2. LOGIN USER & ISSUE JWT TOKEN
router.post('/login', async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email and password are required.' });
    }

    let user = null;
    if (db.isMongoConnected) {
      user = await UserModel.findOne({ email: email.toLowerCase() });
    }
    if (!user) {
      user = db.users.find(u => u.email.toLowerCase() === email.toLowerCase());
    }

    if (!user) {
      return res.status(400).json({ error: 'Invalid email or password.' });
    }

    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) {
      return res.status(400).json({ error: 'Invalid email or password.' });
    }

    if (user.accountStatus === 'PENDING_APPROVAL') {
      return res.status(403).json({
        error: 'Your Legal Metrology Officer account is pending verification by the District Controller.'
      });
    }

    // Issue 24-hour JWT Token
    const token = jwt.sign(
      {
        userId: user.id,
        email: user.email,
        name: user.name,
        role: user.role,
        district: user.district || 'General',
        employeeId: user.employeeId
      },
      JWT_SECRET,
      { expiresIn: '24h' }
    );

    res.json({
      success: true,
      message: 'Login successful!',
      token: token,
      user: {
        id: user.id,
        name: user.name,
        email: user.email,
        role: user.role,
        district: user.district,
        employeeId: user.employeeId
      }
    });

  } catch (error) {
    console.error('Login Route Error:', error);
    res.status(500).json({ error: 'Login failed: ' + error.message });
  }
});

// 3. GET CURRENT USER PROFILE
router.get('/me', (req, res) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];
  if (!token) return res.status(401).json({ error: 'Token missing' });

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    res.json({ user: decoded });
  } catch (e) {
    res.status(401).json({ error: 'Invalid token' });
  }
});

module.exports = router;
