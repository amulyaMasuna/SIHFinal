import React from 'react';

export default function ResultView({ result, imagePreview, onReset }) {
  if (!result) return null;

  const isCompliant = result.status === 'PASS';

  return (
    <div class="max-w-6xl mx-auto space-y-6">
      
      {/* Top Banner Status */}
      <div class={`p-6 rounded-2xl border shadow-xl flex items-center justify-between ${
        isCompliant
          ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-300'
          : 'bg-red-950/40 border-red-500/40 text-red-300'
      }`}>
        <div class="flex items-center space-x-4">
          <div class={`text-4xl p-3 rounded-xl ${isCompliant ? 'bg-emerald-500/20' : 'bg-red-500/20'}`}>
            {isCompliant ? '🟢' : '🔴'}
          </div>
          <div>
            <div class="flex items-center space-x-2">
              <span class={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase ${
                isCompliant ? 'bg-emerald-500 text-slate-950' : 'bg-red-500 text-white'
              }`}>
                {result.status}
              </span>
              <span class="text-xs text-slate-400">ID: {result.inspectionId || 'INSP-TEMP'}</span>
            </div>
            <h2 class="text-2xl font-black text-white mt-1">
              {isCompliant ? 'COMPLIANT PACKAGE LABEL' : 'STATUTORY NON-COMPLIANCE DETECTED'}
            </h2>
            <p class="text-xs text-slate-300 mt-0.5">
              {isCompliant
                ? 'All mandatory declarations under Legal Metrology Rules, 2011 are valid.'
                : `Identified ${result.total_violations} statutory violation(s) under Legal Metrology Act, 2009.`}
            </p>
          </div>
        </div>

        <button
          onClick={onReset}
          class="px-5 py-2.5 text-sm font-bold bg-slate-800 hover:bg-slate-700 text-white rounded-xl border border-slate-600 transition-colors"
        >
          📷 New Scan
        </button>
      </div>

      {/* DUAL PANE WORKBENCH */}
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Pane: Image & Bounding Box Viewer */}
        <div class="lg:col-span-5 bg-slate-800 border border-slate-700 rounded-2xl p-4 shadow-xl flex flex-col">
          <h3 class="text-sm font-bold text-slate-200 mb-3 flex items-center justify-between">
            <span>🖼️ Packaging Image &amp; AI Bounding Boxes</span>
            <span class="text-xs text-blue-400 bg-blue-950/60 px-2 py-0.5 rounded border border-blue-800">
              {result.ocr_engine_used || 'PaddleOCR Engine'}
            </span>
          </h3>

          <div class="relative bg-slate-900 rounded-xl overflow-hidden border border-slate-700 flex-1 flex items-center justify-center min-h-[300px]">
            {imagePreview ? (
              <img src={imagePreview} alt="Scanned Package" class="max-h-[450px] w-auto object-contain rounded-lg" />
            ) : (
              <div class="text-center p-8 text-slate-500">
                <p>No preview image available</p>
              </div>
            )}
          </div>

          <div class="mt-3 text-xs text-slate-400 bg-slate-900/60 p-2.5 rounded-lg border border-slate-700">
            💡 <strong class="text-slate-200">OpenCV Preprocessing:</strong> Auto-resized, grayscale converted, and contrast-boosted via CLAHE (`clipLimit=2.0`).
          </div>
        </div>

        {/* Right Pane: Violations & Extracted Entities */}
        <div class="lg:col-span-7 space-y-6">
          
          {/* Violations List */}
          {!isCompliant && (
            <div class="bg-slate-800 border border-red-500/30 rounded-2xl p-5 shadow-xl">
              <h3 class="text-sm font-bold text-red-400 mb-3 flex items-center space-x-2">
                <span>⚠️ Itemized Statutory Violations ({result.violations?.length || 0})</span>
              </h3>

              <div class="space-y-3">
                {result.violations?.map((v, i) => (
                  <div key={i} class="bg-slate-900 p-3.5 rounded-xl border border-red-900/40 text-xs">
                    <div class="flex items-center justify-between mb-1">
                      <span class="font-bold text-red-400 bg-red-950/80 px-2 py-0.5 rounded border border-red-800">
                        [{v.rule}] {v.category || 'Violation'}
                      </span>
                      <span class="text-amber-400 font-bold uppercase">{v.severity || 'MAJOR'}</span>
                    </div>
                    {v.found && (
                      <p class="text-slate-300 mt-1">
                        <strong>Found Text:</strong> <code class="bg-slate-950 px-1.5 py-0.5 rounded text-amber-300">{v.found}</code>
                      </p>
                    )}
                    <p class="text-slate-300 mt-1"><strong>Issue:</strong> {v.issue}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Extracted Entities Table */}
          <div class="bg-slate-800 border border-slate-700 rounded-2xl p-5 shadow-xl">
            <h3 class="text-sm font-bold text-slate-200 mb-3">
              📋 Extracted Mandatory Declarations (JSON Metadata)
            </h3>

            <div class="bg-slate-900 rounded-xl overflow-hidden border border-slate-700 text-xs divide-y divide-slate-800">
              <div class="grid grid-cols-3 p-3 font-bold text-slate-400 bg-slate-950/60">
                <span>Mandatory Field</span>
                <span class="col-span-2">Extracted Value / Status</span>
              </div>

              <div class="grid grid-cols-3 p-3">
                <span class="font-semibold text-slate-300">1. MRP Declaration</span>
                <span class="col-span-2 text-white font-mono">{result.parsed_entities?.mrp_raw || '❌ Missing'}</span>
              </div>

              <div class="grid grid-cols-3 p-3">
                <span class="font-semibold text-slate-300">2. Net Quantity</span>
                <span class="col-span-2 text-white font-mono">{result.parsed_entities?.net_qty_raw || '❌ Missing'}</span>
              </div>

              <div class="grid grid-cols-3 p-3">
                <span class="font-semibold text-slate-300">3. Mfg / Packing Date</span>
                <span class="col-span-2 text-white font-mono">{result.parsed_entities?.mfg_date_raw || '❌ Missing'}</span>
              </div>

              <div class="grid grid-cols-3 p-3">
                <span class="font-semibold text-slate-300">4. Manufacturer Address</span>
                <span class="col-span-2 text-white font-mono">{result.parsed_entities?.manufacturer_details || '❌ Missing'}</span>
              </div>

              <div class="grid grid-cols-3 p-3">
                <span class="font-semibold text-slate-300">5. Consumer Care Email</span>
                <span class="col-span-2 text-white font-mono">{result.parsed_entities?.consumer_care_email || '❌ Missing'}</span>
              </div>

              <div class="grid grid-cols-3 p-3">
                <span class="font-semibold text-slate-300">6. Country of Origin</span>
                <span class="col-span-2 text-white font-mono">{result.parsed_entities?.country_of_origin || 'India (Default)'}</span>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
