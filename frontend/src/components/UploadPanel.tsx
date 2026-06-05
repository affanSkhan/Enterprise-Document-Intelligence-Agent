"use client";
import { useState } from 'react';

export default function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setMessage('');
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
      const res = await fetch('http://localhost:8000/api/documents/upload', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      if (res.ok) {
        setMessage(`Success! ${file.name} uploaded & indexed.`);
        setFile(null);
      } else {
        setMessage(`Error: ${data.detail || 'Upload failed'}`);
      }
    } catch (error) {
      setMessage('Network error.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <h2 className="text-lg font-medium mb-4 flex items-center gap-2">
        <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        Upload Document
      </h2>
      <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center hover:border-indigo-500/50 hover:bg-indigo-500/5 transition-all">
        <input 
          type="file" 
          id="file-upload" 
          className="hidden" 
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center">
          <svg className="w-10 h-10 text-neutral-400 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <span className="text-sm font-medium text-neutral-300">
            {file ? file.name : "Click to select a file"}
          </span>
          <span className="text-xs text-neutral-500 mt-1">PDF, DOCX, PPTX, XLSX, TXT up to 50MB</span>
        </label>
      </div>
      <button 
        onClick={handleUpload}
        disabled={!file || isUploading}
        className="w-full mt-4 bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {isUploading ? (
          <>
            <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Processing...
          </>
        ) : "Upload & Index"}
      </button>
      {message && <p className="mt-3 text-sm text-center text-indigo-300">{message}</p>}
    </div>
  );
}
