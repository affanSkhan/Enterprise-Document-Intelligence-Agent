"use client";
import { useState } from 'react';
import ReactMarkdown from 'react-markdown';

type Action = 'report' | 'presentation' | 'bom';
type Slide = { title: string; bullet_points: string[] };
type BomItem = { part_number: string; description: string; quantity: string | number };
type AgentOutput = string | Slide[] | BomItem[] | { error: string; raw?: string; details?: string } | null;

type AgentResponse = { result?: AgentOutput };

const actions: Action[] = ['report', 'presentation', 'bom'];

export default function AgentActions() {
  const [topic, setTopic] = useState('');
  const [output, setOutput] = useState<AgentOutput>(null);
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState<Action>('report');

  const handleRunAgent = async () => {
    if (!topic.trim()) return;
    setLoading(true);
    setOutput(null);
    const endpoint = action === 'report' ? '/api/agents/report' : action === 'presentation' ? '/api/agents/presentation' : '/api/agents/bom';
    const payload = action === 'bom' ? { doc_id: topic } : { topic };

    try {
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const data = (await res.json()) as AgentResponse;
      if (!res.ok) throw new Error(typeof data.result === 'object' && data.result && 'error' in data.result ? data.result.error : 'Agent request failed');
      setOutput(data.result ?? null);
    } catch (error) {
      setOutput({ error: error instanceof Error ? error.message : 'Failed to run agent' });
    } finally { setLoading(false); }
  };

  const slides = Array.isArray(output) && output.length > 0 && 'title' in output[0] ? output as Slide[] : null;
  const bom = Array.isArray(output) && output.length > 0 && 'part_number' in output[0] ? output as BomItem[] : null;
  const errorOutput = output && !Array.isArray(output) && typeof output === 'object' && 'error' in output ? output : null;

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-6"><h2 className="text-xl font-medium">Specialized Agents</h2></div>
      <div className="flex gap-4 mb-6">
        {actions.map((type) => <button key={type} onClick={() => setAction(type)} className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${action === type ? 'bg-pink-500 text-white' : 'bg-white/5 text-neutral-400 hover:bg-white/10'}`}>{type.charAt(0).toUpperCase() + type.slice(1)} Agent</button>)}
      </div>
      <div className="flex gap-3 mb-8">
        <input type="text" value={topic} onChange={(e) => setTopic(e.target.value)} placeholder={action === 'bom' ? 'Enter Document ID for BOM extraction...' : 'Enter a topic for the agent...'} className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-pink-500 transition-colors placeholder-neutral-500" />
        <button onClick={handleRunAgent} disabled={!topic.trim() || loading} className="bg-pink-600 hover:bg-pink-500 text-white px-6 py-3 rounded-xl transition-all disabled:opacity-50 font-medium">{loading ? 'Running…' : 'Generate'}</button>
      </div>
      {output && (
        <div className="bg-black/30 border border-white/10 rounded-xl p-6 overflow-auto max-h-[500px]">
          <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-4">Agent Output</h3>
          {typeof output === 'string' && <div className="prose prose-invert max-w-none prose-sm sm:prose-base text-neutral-200"><ReactMarkdown>{output}</ReactMarkdown></div>}
          {slides && <div className="space-y-6">{slides.map((slide, idx) => <div key={`${slide.title}-${idx}`} className="bg-black/40 border border-white/10 rounded-xl p-6"><div className="text-xs text-pink-400 mb-2 uppercase">Slide {idx + 1}</div><h4 className="text-xl font-semibold text-white mb-4">{slide.title}</h4><ul className="list-disc ml-5 space-y-2 text-neutral-300">{slide.bullet_points.map((bp, i) => <li key={`${i}-${bp}`}><ReactMarkdown components={{ p: 'span' }}>{bp}</ReactMarkdown></li>)}</ul></div>)}</div>}
          {bom && <div className="overflow-x-auto"><table className="w-full text-left text-sm text-neutral-300"><thead className="text-xs uppercase bg-black/40 text-neutral-400"><tr><th className="px-6 py-3">Part Number</th><th className="px-6 py-3">Description</th><th className="px-6 py-3">Quantity</th></tr></thead><tbody>{bom.map((item, idx) => <tr key={`${item.part_number}-${idx}`} className="border-b border-white/5"><td className="px-6 py-4 font-medium text-white">{item.part_number}</td><td className="px-6 py-4">{item.description}</td><td className="px-6 py-4">{item.quantity}</td></tr>)}</tbody></table></div>}
          {errorOutput && <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6 text-red-400"><span className="font-semibold">{errorOutput.error}</span>{errorOutput.raw && <pre className="mt-4 text-sm whitespace-pre-wrap">{errorOutput.raw}</pre>}</div>}
          {Array.isArray(output) && output.length === 0 && <div className="text-neutral-400 italic">No data was found or extracted.</div>}
          {!Array.isArray(output) && typeof output === 'object' && output && !('error' in output) && <pre className="text-sm text-neutral-300 whitespace-pre-wrap">{JSON.stringify(output, null, 2)}</pre>}
        </div>
      )}
    </div>
  );
}
