"use client";
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

export default function AgentActions() {
  const [topic, setTopic] = useState('');
  const [output, setOutput] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<'report' | 'presentation' | 'bom'>('report');

  const handleRunAgent = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setOutput(null);

    const endpoint = action === 'report' ? '/api/agents/report' 
                   : action === 'presentation' ? '/api/agents/presentation' 
                   : '/api/agents/bom';
                   
    const payload = action === 'bom' ? { doc_id: topic } : { topic };

    try {
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setOutput(data.result);
    } catch (error) {
      console.error(error);
      setOutput({ error: 'Failed to run agent' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-8 h-8 rounded bg-pink-500/20 flex items-center justify-center">
          <svg className="w-5 h-5 text-pink-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
        </div>
        <h2 className="text-xl font-medium">Specialized Agents</h2>
      </div>

      <div className="flex gap-4 mb-6">
        {['report', 'presentation', 'bom'].map((type) => (
          <button
            key={type}
            onClick={() => setAction(type as any)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${action === type ? 'bg-pink-500 text-white' : 'bg-white/5 text-neutral-400 hover:bg-white/10'}`}
          >
            {type.charAt(0).toUpperCase() + type.slice(1)} Agent
          </button>
        ))}
      </div>

      <div className="flex gap-3 mb-8">
        <input 
          type="text"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder={action === 'bom' ? "Enter Document ID for BOM extraction..." : "Enter a topic for the agent..."}
          className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-pink-500 transition-colors placeholder-neutral-500"
        />
        <button 
          onClick={handleRunAgent}
          disabled={!topic.trim() || loading}
          className="bg-pink-600 hover:bg-pink-500 text-white px-6 py-3 rounded-xl transition-all disabled:opacity-50 font-medium flex items-center gap-2"
        >
          {loading ? (
             <svg className="animate-spin w-4 h-4" viewBox="0 0 24 24" fill="none">
               <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
               <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
             </svg>
          ) : "Generate"}
        </button>
      </div>

      {output && (
        <div className="bg-black/30 border border-white/10 rounded-xl p-6 overflow-auto max-h-[500px]">
          <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-4">Agent Output</h3>
          {typeof output === 'string' ? (
            <div className="prose prose-invert max-w-none prose-sm sm:prose-base prose-p:leading-relaxed prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 text-neutral-200">
              <ReactMarkdown>{output}</ReactMarkdown>
            </div>
          ) : Array.isArray(output) && output.length > 0 && output[0].title && output[0].bullet_points ? (
            <div className="space-y-6">
              {output.map((slide: any, idx: number) => (
                <div key={idx} className="bg-black/40 border border-white/10 rounded-xl p-6">
                  <div className="text-xs text-pink-400 mb-2 font-medium tracking-widest uppercase">Slide {idx + 1}</div>
                  <h4 className="text-xl font-semibold text-white mb-4">{slide.title}</h4>
                  <ul className="list-disc list-outside ml-5 space-y-2 text-neutral-300">
                    {slide.bullet_points.map((bp: string, i: number) => (
                      <li key={i}><ReactMarkdown components={{ p: 'span' }}>{bp}</ReactMarkdown></li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          ) : Array.isArray(output) && output.length > 0 && output[0].part_number ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-neutral-300">
                <thead className="text-xs uppercase bg-black/40 text-neutral-400">
                  <tr>
                    <th className="px-6 py-3 rounded-tl-lg">Part Number</th>
                    <th className="px-6 py-3">Description</th>
                    <th className="px-6 py-3 rounded-tr-lg">Quantity</th>
                  </tr>
                </thead>
                <tbody>
                  {output.map((item: any, idx: number) => (
                    <tr key={idx} className="border-b border-white/5 bg-white/5 hover:bg-white/10 transition-colors">
                      <td className="px-6 py-4 font-medium text-white">{item.part_number}</td>
                      <td className="px-6 py-4">{item.description}</td>
                      <td className="px-6 py-4">{item.quantity}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : output && output.error ? (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400">
              <div className="flex items-center gap-2 mb-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="font-semibold">{output.error}</span>
              </div>
              {output.raw && (
                <div className="mt-4 text-sm text-red-300/80 bg-black/20 p-3 rounded-lg border border-red-500/10">
                  <span className="block font-medium uppercase tracking-wider text-[10px] mb-1 opacity-70">Agent Response</span>
                  {output.raw}
                </div>
              )}
            </div>
          ) : Array.isArray(output) && output.length === 0 ? (
             <div className="text-neutral-400 italic p-4 bg-black/20 rounded-xl border border-white/5">
               No data was found or extracted for this request.
             </div>
          ) : (
            <pre className="text-sm text-neutral-300 font-mono whitespace-pre-wrap bg-black/40 p-4 rounded-xl border border-white/10 overflow-x-auto">{JSON.stringify(output, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}
