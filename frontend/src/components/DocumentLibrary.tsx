"use client";
import { useState, useEffect } from 'react';

type Document = {
  id: string;
  filename: string;
  file_type: string;
  upload_date: string;
  status: string;
};

export default function DocumentLibrary() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDocs();
  }, []);

  const fetchDocs = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/documents');
      const data = await res.json();
      if (Array.isArray(data)) {
        setDocs(data);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-medium flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
          </svg>
          Document Library
        </h2>
        <button onClick={fetchDocs} className="text-sm text-neutral-400 hover:text-white transition-colors">
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500"></div>
        </div>
      ) : docs.length === 0 ? (
        <div className="text-center py-12 text-neutral-500">
          No documents uploaded yet.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 uppercase bg-black/20">
              <tr>
                <th className="px-4 py-3 rounded-l-lg">Filename</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3 rounded-r-lg">Status</th>
              </tr>
            </thead>
            <tbody>
              {docs.map(doc => (
                <tr key={doc.id} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                  <td className="px-4 py-4 font-medium truncate max-w-xs">{doc.filename}</td>
                  <td className="px-4 py-4"><span className="px-2 py-1 bg-white/10 rounded text-xs">{doc.file_type}</span></td>
                  <td className="px-4 py-4 text-neutral-400">{new Date(doc.upload_date).toLocaleDateString()}</td>
                  <td className="px-4 py-4">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${doc.status === 'INDEXED' ? 'bg-green-500/20 text-green-400' : doc.status === 'ERROR' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                      {doc.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
