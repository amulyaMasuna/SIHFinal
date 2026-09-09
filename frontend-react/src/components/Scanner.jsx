import React, { useState, useRef } from 'react';
import api from '../services/api';

export default function Scanner({ onScanComplete }) {
  const [uploadOption, setUploadOption] = useState('file'); // 'file' or 'camera'
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [cameraActive, setCameraActive] = useState(false);

  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  // File Picker / Drag and Drop Handler
  const handleFileSelect = (e) => {
    const file = e.target.files ? e.target.files[0] : null;
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  // Start HTML5 Live Camera
  const startCamera = async () => {
    setUploadOption('camera');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
      });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setCameraActive(true);
      }
    } catch (err) {
      alert('Camera access denied or unsupported: ' + err.message);
    }
  };

  // Capture Photo from Live Camera
  const capturePhoto = () => {
    if (!videoRef.current || !canvasRef.current) return;
    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth || 1280;
    canvas.height = video.videoHeight || 720;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      const file = new File([blob], 'camera_capture.jpg', { type: 'image/jpeg' });
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));

      // Stop camera stream
      if (video.srcObject) {
        video.srcObject.getTracks().forEach(t => t.stop());
      }
      setCameraActive(false);
    }, 'image/jpeg', 0.95);
  };

  // Single Analyze Button Execution
  const handleAnalyze = async () => {
    if (!selectedFile) {
      alert('Please select an image file or capture a photo first!');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('image', selectedFile);
    formData.append('productName', selectedFile.name || 'Packaging Label');

    try {
      const res = await api.post('/inspect', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      onScanComplete(res.data, previewUrl);
    } catch (err) {
      alert('Analysis failed: ' + (err.response?.data?.error || err.message));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div class="max-w-2xl mx-auto bg-slate-800/80 backdrop-blur-md border border-slate-700 rounded-3xl p-6 shadow-2xl space-y-6">
      
      {/* 2 Upload Ways Selector */}
      <div class="grid grid-cols-2 gap-3 bg-slate-900/80 p-1.5 rounded-2xl border border-slate-700/60">
        <button
          type="button"
          onClick={() => { setUploadOption('file'); setCameraActive(false); }}
          class={`py-3 rounded-xl font-semibold text-sm transition-all flex items-center justify-center space-x-2 ${
            uploadOption === 'file'
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <span>📁</span>
          <span>Upload Image</span>
        </button>

        <button
          type="button"
          onClick={startCamera}
          class={`py-3 rounded-xl font-semibold text-sm transition-all flex items-center justify-center space-x-2 ${
            uploadOption === 'camera'
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          <span>📷</span>
          <span>In-Browser Camera</span>
        </button>
      </div>

      {/* OPTION 1: DRAG & DROP / FILE SELECTOR */}
      {uploadOption === 'file' && (
        <div
          onDragOver={(e) => e.preventDefault()}
          onDrop={handleDrop}
          class="border-2 border-dashed border-slate-600 hover:border-blue-500 rounded-2xl p-8 text-center bg-slate-900/40 transition-all cursor-pointer"
        >
          <input
            type="file"
            accept="image/*"
            onChange={handleFileSelect}
            id="fileInput"
            class="hidden"
          />
          <label htmlFor="fileInput" class="cursor-pointer space-y-3 block">
            <div class="w-16 h-16 mx-auto bg-blue-950/60 rounded-full flex items-center justify-center text-3xl border border-blue-800 text-blue-400">
              📤
            </div>
            <div>
              <p class="text-base font-bold text-white">Drag & drop package label image</p>
              <p class="text-xs text-slate-400 mt-1">or click to browse from device (JPEG, PNG, WebP)</p>
            </div>
          </label>
        </div>
      )}

      {/* OPTION 2: IN-BROWSER LIVE CAMERA SCANNER */}
      {uploadOption === 'camera' && (
        <div class="space-y-4 text-center">
          {cameraActive ? (
            <div class="relative max-w-md mx-auto rounded-2xl overflow-hidden border-2 border-blue-500 bg-black aspect-video">
              <video ref={videoRef} autoPlay playsInline class="w-full h-full object-cover"></video>
              <div class="absolute inset-4 border-2 border-dashed border-emerald-400/80 pointer-events-none rounded-lg flex items-center justify-center">
                <span class="text-xs font-bold text-emerald-300 bg-black/70 px-3 py-1 rounded-full">
                  Position Label Here
                </span>
              </div>
            </div>
          ) : null}

          <canvas ref={canvasRef} class="hidden"></canvas>

          {cameraActive && (
            <button
              type="button"
              onClick={capturePhoto}
              class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm rounded-xl shadow-md transition-all"
            >
              📸 Snap Photo
            </button>
          )}
        </div>
      )}

      {/* SELECTED IMAGE PREVIEW DISPLAY */}
      {previewUrl && (
        <div class="bg-slate-900 p-3 rounded-2xl border border-slate-700 flex items-center justify-between">
          <div class="flex items-center space-x-3">
            <img src={previewUrl} alt="Label Preview" class="w-14 h-14 object-cover rounded-xl border border-slate-700" />
            <div>
              <p class="text-sm font-bold text-white truncate max-w-[200px]">{selectedFile?.name || 'Captured Image'}</p>
              <p class="text-xs text-emerald-400 font-semibold">✓ Image Ready for AI Analysis</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => { setSelectedFile(null); setPreviewUrl(''); }}
            class="text-xs text-slate-400 hover:text-rose-400 px-3 py-1 bg-slate-800 rounded-lg"
          >
            Remove
          </button>
        </div>
      )}

      {/* ONE SINGLE BUTTON TO ANALYZE */}
      <button
        type="button"
        onClick={handleAnalyze}
        disabled={loading || !selectedFile}
        class="w-full py-4 bg-gradient-to-r from-blue-600 via-indigo-600 to-blue-600 hover:from-blue-500 hover:to-indigo-500 text-white font-black text-base rounded-2xl shadow-xl transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
      >
        {loading ? (
          <>
            <span class="animate-spin text-lg">⚙️</span>
            <span>Running Legal Metrology Compliance Check...</span>
          </>
        ) : (
          <span>🔍 Analyze Package Image</span>
        )}
      </button>

    </div>
  );
}
