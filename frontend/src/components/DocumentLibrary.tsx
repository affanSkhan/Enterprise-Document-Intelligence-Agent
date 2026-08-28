"use client";
import { useCallback, useEffect, useState } from "react";
import { api, type Document } from "@/lib/api";

export default function DocumentLibrary() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchDocs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setDocs(await api.documents());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load documents.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void fetchDocs(); }, [fetchDocs]);

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6"><h2 className="text-xl font-medium">Document Library</h2><button onClick={() => void fetchDocs()} className="text-sm text-neutral-400 hover:text-white">Refresh</button></div>
      {loading ? <div className="flex justify-center py-12"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-500" /></div> : error ? <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-300">{error}</div> : docs.length === 0 ? <div className="text-center py-12 text-neutral-500">No documents uploaded yet.</div> : <div className="overflow-x-auto"><table className="w-full text-sm text-left"><thead className="text-xs text-neutral-400 uppercase bg-black/20"><tr><th className="px-4 py-3">Filename</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Date</th><th className="px-4 py-3">Status</th></tr></thead><tbody>{docs.map((doc) => <tr key={doc.id} className="border-b border-white/5 hover:bg-white/5"><td className="px-4 py-4 font-medium truncate max-w-xs">{doc.filename}</td><td className="px-4 py-4"><span className="px-2 py-1 bg-white/10 rounded text-xs">{doc.file_type}</span></td><td className="px-4 py-4 text-neutral-400">{new Date(doc.created_at).toLocaleDateString()}</td><td className="px-4 py-4"><span className={`px-2 py-1 rounded text-xs font-medium ${String(doc.status).toUpperCase() === "INDEXED" ? "bg-green-500/20 text-green-400" : String(doc.status).toUpperCase() === "ERROR" ? "bg-red-500/20 text-red-400" : "bg-yellow-500/20 text-yellow-400"}`}>{doc.status}</span></td></tr>)}</tbody></table></div>}
    </div>
  );
}
