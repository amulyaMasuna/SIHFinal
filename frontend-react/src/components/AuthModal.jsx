import React, { useState } from 'react';
import api from '../services/api';

export default function AuthModal({ isOpen, onClose, onLoginSuccess }) {
  const [isRegister, setIsRegister] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    role: 'CONSUMER',
    employeeId: '',
    district: 'Pune'
  });

  if (!isOpen) return null;

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setMsg('');
    setLoading(true);

    try {
      if (isRegister) {
        // Register API Call
        const res = await api.post('/auth/register', formData);
        setMsg(res.data.message || 'Registration successful!');
        setTimeout(() => setIsRegister(false), 1500);
      } else {
        // Login API Call
        const res = await api.post('/auth/login', {
          email: formData.email,
          password: formData.password
        });

        // Store JWT token and user payload in localStorage
        localStorage.setItem('token', res.data.token);
        localStorage.setItem('user', JSON.stringify(res.data.user));

        onLoginSuccess(res.data.user);
        onClose();
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Authentication request failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div class="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div class="bg-slate-800 border border-slate-700 w-full max-w-md rounded-2xl p-6 shadow-2xl relative">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          class="absolute top-4 right-4 text-slate-400 hover:text-white font-bold"
        >
          ✕
        </button>

        <h2 class="text-xl font-bold text-white mb-1">
          {isRegister ? 'Register Account' : 'System Login'}
        </h2>
        <p class="text-xs text-slate-400 mb-4">
          Enter credentials to access system features
        </p>

        {error && (
          <div class="mb-4 p-3 bg-red-950/60 border border-red-800 text-red-300 text-xs rounded-lg">
            {error}
          </div>
        )}

        {msg && (
          <div class="mb-4 p-3 bg-emerald-950/60 border border-emerald-800 text-emerald-300 text-xs rounded-lg">
            {msg}
          </div>
        )}

        <form onSubmit={handleSubmit} class="space-y-3 text-sm">
          {isRegister && (
            <div>
              <label class="block text-xs font-semibold text-slate-300 mb-1">Full Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                placeholder="e.g. Dr. V. K. Patil"
              />
            </div>
          )}

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">
              Email Address {isRegister && formData.role === 'LEGAL_METROLOGY_OFFICER' && '(Requires .gov.in or .nic.in)'}
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              placeholder="e.g. officer@nic.in"
            />
          </div>

          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-1">Password</label>
            <input
              type="password"
              name="password"
              value={formData.password}
              onChange={handleChange}
              required
              class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
              placeholder="••••••••"
            />
          </div>

          {isRegister && (
            <>
              <div>
                <label class="block text-xs font-semibold text-slate-300 mb-1">System Role</label>
                <select
                  name="role"
                  value={formData.role}
                  onChange={handleChange}
                  class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                >
                  <option value="CONSUMER">👤 Consumer / Field Inspector</option>
                  <option value="LEGAL_METROLOGY_OFFICER">⚖️ Legal Metrology Officer (Admin)</option>
                </select>
              </div>

              {formData.role === 'LEGAL_METROLOGY_OFFICER' && (
                <div>
                  <label class="block text-xs font-semibold text-slate-300 mb-1">Department Employee ID</label>
                  <input
                    type="text"
                    name="employeeId"
                    value={formData.employeeId}
                    onChange={handleChange}
                    class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                    placeholder="e.g. LMO-MH-2024-88"
                  />
                </div>
              )}
            </>
          )}

          <button
            type="submit"
            disabled={loading}
            class="w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white font-bold text-sm rounded-lg shadow-lg transition-colors mt-2"
          >
            {loading ? 'Processing...' : isRegister ? 'Register' : 'Login'}
          </button>
        </form>

        <div class="mt-4 pt-3 border-t border-slate-700 text-center text-xs text-slate-400">
          {isRegister ? (
            <p>
              Already have an account?{' '}
              <button onClick={() => setIsRegister(false)} class="text-blue-400 font-semibold underline">
                Log in here
              </button>
            </p>
          ) : (
            <p>
              Don't have an account?{' '}
              <button onClick={() => setIsRegister(true)} class="text-blue-400 font-semibold underline">
                Register new account
              </button>
            </p>
          )}
        </div>

      </div>
    </div>
  );
}
