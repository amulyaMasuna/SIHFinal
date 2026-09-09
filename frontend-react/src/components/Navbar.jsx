import React from 'react';

export default function Navbar({ user, onOpenAuth, onLogout, activeTab, setActiveTab }) {
  return (
    <header class="bg-slate-800/90 backdrop-blur border-b border-slate-700 sticky top-0 z-50">
      <div class="max-w-7xl mx-auto px-4 py-3 fill-current flex items-center justify-between">
        
        {/* Logo & System Title */}
        <div class="flex items-center space-x-3 cursor-pointer" onClick={() => setActiveTab('scanner')}>
          <div class="bg-blue-600 p-2 rounded-lg text-white font-bold text-lg shadow-lg">
            ⚖️
          </div>
          <div>
            <h1 class="text-lg font-bold text-white tracking-wide">LegalLens</h1>
            <p class="text-xs text-slate-400">Automated Packaged Commodities Compliance System</p>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div class="flex items-center space-x-2">
          <button
            onClick={() => setActiveTab('scanner')}
            class={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
              activeTab === 'scanner'
                ? 'bg-blue-600 text-white'
                : 'text-slate-300 hover:bg-slate-700'
            }`}
          >
            📷 Label Scanner
          </button>

          {user && (
            <button
              onClick={() => setActiveTab('dashboard')}
              class={`px-4 py-2 text-sm font-semibold rounded-lg transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-700'
              }`}
            >
              📊 {user.role === 'LEGAL_METROLOGY_OFFICER' ? 'Officer Portal' : 'My History'}
            </button>
          )}

          {/* User Auth / Profile Badge */}
          {user ? (
            <div class="flex items-center space-x-3 border-l border-slate-700 pl-4">
              <div class="text-right">
                <p class="text-sm font-bold text-slate-100">{user.name}</p>
                <span class={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                  user.role === 'LEGAL_METROLOGY_OFFICER' 
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' 
                    : 'bg-blue-500/20 text-blue-300'
                }`}>
                  {user.role === 'LEGAL_METROLOGY_OFFICER' ? '⚖️ Legal Officer' : '👤 Consumer'}
                </span>
              </div>
              <button
                onClick={onLogout}
                class="px-3 py-1.5 text-xs font-semibold text-red-400 bg-red-950/40 hover:bg-red-900/50 border border-red-800/60 rounded-lg transition-colors"
              >
                Logout
              </button>
            </div>
          ) : (
            <div class="border-l border-slate-700 pl-4 flex items-center space-x-2">
              <span class="text-xs text-slate-400 px-2 py-1 bg-slate-900/80 rounded border border-slate-700">
                Mode: Guest
              </span>
              <button
                onClick={onOpenAuth}
                class="px-4 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-500 rounded-lg shadow transition-colors"
              >
                🔐 Log in / Register
              </button>
            </div>
          )}

        </div>
      </div>
    </header>
  );
}
