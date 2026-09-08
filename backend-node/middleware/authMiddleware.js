const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'sih26034_secret_key_2026';

// 1. Verify JWT Token Middleware
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1]; // Extract Bearer token

  if (!token) {
    return res.status(401).json({ error: "Access denied. Token missing from Authorization header." });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded; // Attach user payload { userId, email, role, district } to request
    next();
  } catch (error) {
    return res.status(403).json({ error: "Invalid or expired JWT token." });
  }
};

// 2. Optional JWT Authentication Middleware (For Guest or Logged In users)
const optionalToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (token) {
    try {
      const decoded = jwt.verify(token, JWT_SECRET);
      req.user = decoded;
    } catch (e) {
      // Ignore token errors for guest requests
    }
  }
  next();
};

// 3. Role-Based Access Control (RBAC) Middleware
const requireRole = (...allowedRoles) => {
  return (req, res, next) => {
    if (!req.user || !allowedRoles.includes(req.user.role)) {
      return res.status(403).json({
        error: `Access denied. Authorized roles: [${allowedRoles.join(', ')}]. Your role: '${req.user ? req.user.role : 'GUEST'}'`
      });
    }
    next();
  };
};

module.exports = { authenticateToken, optionalToken, requireRole, JWT_SECRET };
