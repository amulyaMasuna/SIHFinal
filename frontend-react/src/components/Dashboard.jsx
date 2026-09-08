import React, { useState, useEffect } from 'react';
import api from '../services/api';

export default function Dashboard({ user }) {
  const [flaggedCases, setFlaggedCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dispatchStatus, setDispatchStatus] = useState({});

  const isOfficer = user && user.role === 'LEGAL_METROLOGY_OFFICER';

  useEffect(() => {
    fetchDashboardData();
  }, [user]);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      if (isOfficer) {
        // Fetch Officer Flagged Cases Queue
        const res = await api.get('/officer/flagged-cases');
        setFlaggedCases(res.data.cases || []);
      } else {
        // Fetch User's Scans
        const res = await api.get('/history');
        setFlaggedCases(res.data.history || []);
      }
    } catch (err) {
      console.error('Failed to load dashboard:', err);
    } finally {
      setLoading(false);
    }
  };

  // Download Statutory Legal Notice PDF
  const handleDownloadPDF = async (inspectionId) => {
    try {
      const response = await api.get(`/officer/notice-pdf/${inspectionId}`, {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Statutory_Notice_${inspectionId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('PDF generation failed: ' + err.message);
    }
  };

  // Trigger Automated Notice Issuance to Manufacturer
  const handleAutoDispatch = async (inspectionId) => {
    setDispatchStatus({ ...dispatchStatus, [inspectionId]: 'sending' });
    try {
      const res = await api.post(`/officer/issue-notice/${inspectionId}`);
      setDispatchStatus({ ...dispatchStatus, [inspectionId]: 'sent' });
      alert(res.data.message || 'Statutory legal notice dispatched to manufacturer!');
      fetchDashboardData();
    } catch (err) {
      setDispatchStatus({ ...dispatchStatus, [inspectionId]: 'failed' });
      alert('Notice dispatch failed: ' + err.message);
    }
  };

  return (
    <div class="max-w-7xl mx-auto space-y-6">
      
      {/* Header Banner */}
      <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-xl flex items-center justify-between">
        <div>
          <h2 class="text-2xl font-extrabold text-white">
            {isOfficer ? '⚖️ Legal Metrology Officer Enforcement Portal' : '📊 My Inspection History'}
          </h2>
          <p class="text-xs text-slate-400 mt-1">
            {isOfficer 
              ? `Assigned Jurisdiction: District ${user.district || 'Pune'} • Authorized Sec 36 Enforcement Division`
              : 'Historical scan logs and compliance records'}
          </p>
        </div>

        <button
          onClick={fetchDashboardData}
          class="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-xs font-bold text-white rounded-xl transition-colors"
        >
          🔄 Refresh Queue
        </button>
      </div>

      {/* KPI METRIC CARDS */}
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-slate-800 border border-slate-700 p-5 rounded-2xl shadow-lg">
          <p class="text-xs font-semibold text-slate-400 uppercase">Total Scans</p>
          <h3 class="text-3xl font-black text-white mt-1">{flaggedCases.length + 12}</h3>
          <span class="text-xs text-emerald-400 mt-1 block">↑ +18% this month</span>
        </div>

        <div class="bg-slate-800 border border-slate-700 p-5 rounded-2xl shadow-lg">
          <p class="text-xs font-semibold text-slate-400 uppercase">Flagged Violations Queue</p>
          <h3 class="text-3xl font-black text-amber-400 mt-1">{flaggedCases.length}</h3>
          <span class="text-xs text-amber-400/80 mt-1 block">Pending Officer Review</span>
        </div>

        <div class="bg-slate-800 border border-slate-700 p-5 rounded-2xl shadow-lg">
          <p class="text-xs font-semibold text-slate-400 uppercase">Compliance Rate</p>
          <h3 class="text-3xl font-black text-emerald-400 mt-1">84.2%</h3>
          <span class="text-xs text-slate-400 mt-1 block">DILRMP Benchmark</span>
        </div>

        <div class="bg-slate-800 border border-slate-700 p-5 rounded-2xl shadow-lg">
          <p class="text-xs font-semibold text-slate-400 uppercase">Notices Issued</p>
          <h3 class="text-3xl font-black text-blue-400 mt-1">
            {flaggedCases.filter(c => c.noticeIssued).length}
          </h3>
          <span class="text-xs text-blue-400 mt-1 block">Sec 36 Statutory Notices</span>
        </div>
      </div>

      {/* FLAGGED CASES QUEUE / HISTORY TABLE */}
      <div class="bg-slate-800 border border-slate-700 rounded-2xl p-6 shadow-xl space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-base font-bold text-white">
            {isOfficer ? '🚨 Flagged Non-Compliant Products Queue (Sec 36 Action)' : '📋 Scanned Products History'}
          </h3>
          <span class="text-xs text-slate-400">Filter: Active Jurisdiction</span>
        </div>

        {loading ? (
          <div class="text-center py-12 text-slate-400">Loading cases queue...</div>
        ) : flaggedCases.length === 0 ? (
          <div class="text-center py-12 text-slate-500 bg-slate-900/50 rounded-xl border border-slate-700">
            No flagged violation cases currently pending in queue.
          </div>
        ) : (
          <div class="overflow-x-auto">
            <table class="w-full text-left text-xs border-collapse">
              <thead>
                <tr class="bg-slate-900/90 text-slate-400 font-bold border-b border-slate-700">
                  <th class="p-3.5">Inspection Ref</th>
                  <th class="p-3.5">Product / Manufacturer</th>
                  <th class="p-3.5">Violations Flagged</th>
                  <th class="p-3.5">Status</th>
                  {isOfficer && <th class="p-3.5 text-right">Legal Actions</th>}
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-700/60 text-slate-200">
                {flaggedCases.map((c) => (
                  <tr key={c.id} class="hover:bg-slate-750 transition-colors">
                    
                    <td class="p-3.5 font-mono">
                      <p class="font-bold text-white">{c.id}</p>
                      <p class="text-[10px] text-slate-400">{new Date(c.timestamp).toLocaleDateString('en-IN')}</p>
                    </td>

                    <td class="p-3.5 max-w-xs">
                      <p class="font-semibold text-white truncate">{c.productName}</p>
                      <p class="text-[10px] text-slate-400 truncate">{c.manufacturer}</p>
                    </td>

                    <td class="p-3.5">
                      <div class="space-y-1">
                        {c.violations?.map((v, i) => (
                          <span key={i} class="inline-block bg-red-950/80 text-red-300 border border-red-800 px-2 py-0.5 rounded text-[10px] mr-1">
                            [{v.rule}] {v.issue}
                          </span>
                        ))}
                      </div>
                    </td>

                    <td class="p-3.5">
                      <span class={`px-2.5 py-1 rounded-full font-bold uppercase text-[10px] ${
                        c.status === 'PASS' 
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' 
                          : 'bg-red-500/20 text-red-300 border border-red-500/40'
                      }`}>
                        {c.status}
                      </span>
                    </td>

                    {isOfficer && (
                      <td class="p-3.5 text-right space-x-2">
                        {/* Download PDF Button */}
                        <button
                          onClick={() => handleDownloadPDF(c.id)}
                          class="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg shadow transition-colors"
                        >
                          📄 Download PDF
                        </button>

                        {/* Auto-Dispatch Button */}
                        <button
                          onClick={() => handleAutoDispatch(c.id)}
                          disabled={c.noticeIssued || dispatchStatus[c.id] === 'sending'}
                          class={`px-3 py-1.5 font-bold rounded-lg transition-colors ${
                            c.noticeIssued
                              ? 'bg-emerald-950 text-emerald-400 border border-emerald-800 cursor-default'
                              : 'bg-amber-600 hover:bg-amber-500 text-white shadow'
                          }`}
                        >
                          {c.noticeIssued ? '✓ Notice Dispatched' : '📩 Auto-Issue Notice'}
                        </button>
                      </td>
                    )}

                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
