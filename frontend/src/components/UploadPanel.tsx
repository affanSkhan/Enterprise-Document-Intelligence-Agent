"use client";
import { useState } from 'react';

export default function UploadPanel() {
  const [file, setFile] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [message, setMessage] = useState('');

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true); setMessage('');
    const formData = new FormData(); formData.append('file', file);
    try {
      const res = await fetch('http://localhost:8000/api/documents/upload', { method: 'POST', body: formData });
      const data = (await res.json()) as { detail?: string };
      if (res.ok) { setMessage(`Success! ${file.name} uploaded & indexed.`); setFile(null); }
      else setMessage(`Error: ${data.detail || 'Upload failed'}`);
    } catch { setMessage('Network error.'); }
    finally { setIsUploading(false); }
  };

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <h2 className="text-lg font-medium mb-4">Upload Document</h2>
      <div className="border-2 border-dashed border-white/10 rounded-xl p-8 text-center hover:border-indigo-500/50 transition-all">
        <input type="file" id="file-upload" className="hidden" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        <label htmlFor="file-upload" className="cursor-pointer flex flex-col items-center"><span className="text-sm font-medium text-neutral-300">{file ? file.name : 'Click to select a file'}</span><span className="text-xs text-neutral-500 mt-1">PDF, DOCX, PPTX, XLSX up to 50MB</span></label>
      </div>
      <button onClick={() => void handleUpload()} disabled={!file || isUploading} className="w-full mt-4 bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-2.5 rounded-xl disabled:opacity-50">{isUploading ? 'Processing...' : 'Upload & Index'}</button>
      {message && <p className="mt-3 text-sm text-center text-indigo-300">{message}</p>}
    </div>
  );
}
