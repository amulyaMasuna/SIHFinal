import axios from 'axios';

// Smart API URL Resolver with production fallback
const getApiBaseUrl = () => {
  if (process.env.REACT_APP_API_URL) {
    return process.env.REACT_APP_API_URL;
  }
  // Auto-detect production environment (e.g. onrender.com / vercel / custom domain)
  if (typeof window !== 'undefined' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
    return 'https://legal-metrology-node-gateway.onrender.com/api/v1';
  }
  // Local development fallback
  return 'http://localhost:5000/api/v1';
};

const API_BASE_URL = getApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000 // 30s timeout to allow Render free tier backend wakeup
});

// Request Interceptor: Attach JWT Token automatically to all API calls
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => Promise.reject(error));

export default api;
