import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import AuthModal from './components/AuthModal';
import Scanner from './components/Scanner';
import ResultView from './components/ResultView';
import Dashboard from './components/Dashboard';

export default function App() {
  const [user, setUser] = useState(null);
  const [activeTab, setActiveTab] = useState('scanner'); // 'scanner', 'result', 'dashboard'
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [currentResult, setCurrentResult] = useState(null);
  const [currentImagePreview, setCurrentImagePreview] = useState(null);

  // Restore logged in user from localStorage
  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch (e) {}
    }
  }, []);

  const handleLoginSuccess = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setUser(null);
    setActiveTab('scanner');
  };

  const handleScanComplete = (resultData, previewUrl) => {
    setCurrentResult(resultData);
    setCurrentImagePreview(previewUrl);
    setActiveTab('result');
  };

  const handleResetScan = () => {
    setCurrentResult(null);
    setCurrentImagePreview(null);
    setActiveTab('scanner');
  };

  return (
    <div class="min-h-screen bg-slate-900 text-slate-100 flex flex-col font-sans">
      
      {/* Navigation Header */}
      <Navbar
        user={user}
        onOpenAuth={() => setIsAuthOpen(true)}
        onLogout={handleLogout}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
      />

      {/* Main Content Area */}
      <main class="flex-1 max-w-7xl w-full mx-auto p-6">
        
        {activeTab === 'scanner' && (
          <div class="space-y-6">
            <div class="text-center max-w-2xl mx-auto space-y-2 mb-8">
              <span class="text-xs font-bold uppercase tracking-wider text-blue-400 bg-blue-950/80 px-3 py-1 rounded-full border border-blue-800">
                Automated Legal Metrology Compliance Checking Platform
              </span>
              <h2 class="text-3xl font-extrabold text-white">
                Scan Packaged Commodity Label
              </h2>
              <p class="text-sm text-slate-400">
                Automatically detect, extract, and validate mandatory declarations under the Legal Metrology (Packaged Commodities) Rules, 2011.
              </p>
            </div>

            <Scanner onScanComplete={handleScanComplete} />
          </div>
        )}

        {activeTab === 'result' && (
          <ResultView
            result={currentResult}
            imagePreview={currentImagePreview}
            onReset={handleResetScan}
          />
        )}

        {activeTab === 'dashboard' && (
          <Dashboard user={user} />
        )}

      </main>

      {/* Footer */}
      <footer class="bg-slate-950 border-t border-slate-800 text-center py-4 text-xs text-slate-500">
        <p>LegalLens • AI-Powered Legal Metrology Packaged Commodities System • Ministry of Consumer Affairs</p>
      </footer>

      {/* Auth Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLoginSuccess={handleLoginSuccess}
      />

    </div>
  );
}
