import React, { useState, useRef } from 'react';
import api from '../services/api';

export default function Scanner({ onScanComplete }) {
  const [activeMode, setActiveMode] = useState('upload'); // 'upload', 'camera', 'url'
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [ecommerceUrl, setEcommerceUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // Handle File Drag & Drop
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  // Start In-Browser Live Camera (HTML5 MediaDevices API)
  const startCamera = async () => {
    setActiveMode('camera');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch (err) {
      alert('Camera access error or unsupported on this device: ' + err.message);
    }
  };

  // Capture Snapshot from Camera
  const captureCameraSnapshot = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const canvas = canvasRef.current;
    const video = videoRef.current;

    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      const capturedFile = new File([blob], 'camera_scan.jpg', { type: 'image/jpeg' });
      setSelectedFile(capturedFile);
      setPreviewUrl(URL.createObjectURL(capturedFile));

      // Stop camera stream
      if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
      }
      setCameraActive(false);
      setActiveMode('upload');
    }, 'image/jpeg', 0.95);
  };

  // Trigger Inspection API Call
  const handleAnalyze = async () => {
    if (!selectedFile && activeMode !== 'url') {
      alert('Please upload or capture a package label image first!');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    if (selectedFile) {
      formData.append('image', selectedFile);
    }
    formData.append('productName', selectedFile ? selectedFile.name : 'E-Commerce Scanned Item');
    formData.append('ecommerceUrl', ecommerceUrl);

    try {
      // POST /api/v1/inspect
      const res = await api.post('/inspect', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      onScanComplete(res.data, previewUrl);
    } catch (err) {
      alert('Scan analysis failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div class="max-w-4xl mx-auto p-6 bg-slate-800 border border-slate-700 rounded-2xl shadow-xl">
      
      {/* Mode Selection Tabs */}
      <div class="flex border-b border-slate-700 mb-6">
        <button
          onClick={() => { setActiveMode('upload'); setCameraActive(false); }}
          class={`flex-1 py-3 text-sm font-bold border-b-2 transition-colors ${
            activeMode === 'upload' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          📁 Upload Image / PDF
        </button>
        <button
          onClick={startCamera}
          class={`flex-1 py-3 text-sm font-bold border-b-2 transition-colors ${
            activeMode === 'camera' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          📷 Live Camera Scan
        </button>
        <button
          onClick={() => { setActiveMode('url'); setCameraActive(false); }}
          class={`flex-1 py-3 text-sm font-bold border-b-2 transition-colors ${
            activeMode === 'url' ? 'border-blue-500 text-blue-400' : 'border-transparent text-slate-400 hover:text-white'
          }`}
        >
          🔗 E-Commerce URL Inspection
        </button>
      </div>

      {/* MODE 1: FILE UPLOAD DROPZONE */}
      {activeMode === 'upload' && (
        <div class="space-y-4">
          <div class="border-2 border-dashed border-slate-600 hover:border-blue-500 rounded-xl p-8 text-center bg-slate-900/50 transition-colors">
            <input
              type="file"
              accept="image/*,.pdf"
              onChange={handleFileChange}
              id="fileInput"
              class="hidden"
            />
            <label htmlFor="fileInput" class="cursor-pointer block">
              <div class="text-4xl mb-2">📸</div>
              <p class="text-sm font-semibold text-slate-200">
                Click to browse or drag & drop packaging label image
              </p>
              <p class="text-xs text-slate-500 mt-1">Supports JPEG, PNG, WebP, PDF proofs</p>
            </label>
          </div>

          {previewUrl && (
            <div class="bg-slate-900 p-4 rounded-xl border border-slate-700 flex items-center justify-between">
              <div class="flex items-center space-x-4">
                <img src={previewUrl} alt="Preview" class="w-16 h-16 object-cover rounded-lg border border-slate-600" />
                <div>
                  <p class="text-sm font-semibold text-white">{selectedFile?.name}</p>
                  <p class="text-xs text-slate-400">{(selectedFile?.size / 1024).toFixed(1)} KB • Ready for AI Pipeline</p>
                </div>
              </div>
              <span class="text-emerald-400 text-xs font-bold bg-emerald-950/60 px-3 py-1 rounded-full border border-emerald-800">
                ✓ Image Ready
              </span>
            </div>
          )}
        </div>
      )}

      {/* MODE 2: IN-BROWSER LIVE CAMERA STREAM */}
      {activeMode === 'camera' && (
        <div class="space-y-4 text-center">
          <div class="relative max-w-lg mx-auto rounded-xl overflow-hidden border-2 border-blue-500 bg-black aspect-video">
            <video ref={videoRef} autoPlay playsInline class="w-full h-full object-cover"></video>
            
            {/* Real-time Framing Grid Overlay */}
            <div class="absolute inset-4 border-2 border-dashed border-emerald-400/70 pointer-events-none flex items-center justify-center">
              <span class="text-xs font-semibold text-emerald-300 bg-black/60 px-3 py-1 rounded">
                Align Principal Display Panel (PDP) Here
              </span>
            </div>
          </div>

          <canvas ref={canvasRef} class="hidden"></canvas>

          <button
            onClick={captureCameraSnapshot}
            class="px-6 py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl shadow-lg transition-colors"
          >
            📸 Capture & Process Label
          </button>
        </div>
      )}

      {/* MODE 3: E-COMMERCE URL INSPECTION */}
      {activeMode === 'url' && (
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-semibold text-slate-300 mb-2">
              Paste E-Commerce Product Detail Page (PDP) Link
            </label>
            <input
              type="url"
              value={ecommerceUrl}
              onChange={(e) => setEcommerceUrl(e.target.value)}
              placeholder="e.g. https://www.amazon.in/dp/B08N5WRWNW or Blinkit / Instamart link"
              class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <p class="text-xs text-slate-400">
            Performs automated web crawling under Rule 6(11) of Legal Metrology Rules 2011 to audit online mandatory declarations.
          </p>
        </div>
      )}

      {/* ANALYZE BUTTON */}
      <div class="mt-6 text-center">
        <button
          onClick={handleAnalyze}
          disabled={loading}
          class="w-full py-4 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-extrabold text-base rounded-xl shadow-xl transition-all disabled:opacity-50"
        >
          {loading ? (
            <span class="flex items-center justify-center space-x-2">
              <span class="animate-spin text-lg">⚙️</span>
              <span>Running OpenCV Preprocessing &amp; PaddleOCR Engine...</span>
            </span>
          ) : (
            '🚀 Run AI Legal Metrology Compliance Inspection'
          )}
        </button>
      </div>

    </div>
  );
}
