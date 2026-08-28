"use client";
import { useEffect, useRef, useState } from "react";
import { api, type Evidence } from "@/lib/api";

type Message = { role: "user" | "assistant"; content: string; citations?: Evidence[] };

function safeText(value: unknown, fallback = "No answer returned."): string {
  if (typeof value === "string") return value;
  if (value == null) return fallback;
  try {
    return JSON.stringify(value);
  } catch {
    return fallback;
  }
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || loading) return;
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);
    try {
      const data = await api.chat(question);
      const answer = safeText(data?.answer);
      const citations = Array.isArray(data?.evidence) ? data.evidence : [];
      setMessages((prev) => [...prev, { role: "assistant", content: answer, citations }]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Could not reach the server.";
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl h-full flex flex-col overflow-hidden">
      <div className="p-4 border-b border-white/10 bg-black/20"><h2 className="font-medium text-neutral-200">Intelligence Chat</h2></div>
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? <div className="text-center text-neutral-500 h-full flex items-center justify-center">Ask any question about your uploaded documents.</div> : messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[80%] rounded-2xl p-4 ${msg.role === "user" ? "bg-indigo-600 text-white" : "bg-white/5 border border-white/10 text-neutral-200"}`}>
              <p className="whitespace-pre-wrap break-words">{msg.content}</p>
              {msg.citations && msg.citations.length > 0 && <div className="mt-3 pt-3 border-t border-white/10"><p className="text-xs text-neutral-400 mb-2 uppercase">Sources</p><div className="flex flex-wrap gap-2">{msg.citations.map((cit, idx) => <span key={idx} className="text-xs px-2 py-1 bg-black/30 rounded text-neutral-300 border border-white/5">{cit.metadata?.filename || "Document"}</span>)}</div></div>}
            </div>
          </div>
        ))}
        {loading && <div className="flex justify-start"><div className="bg-white/5 border border-white/10 rounded-2xl p-4 text-neutral-400">Thinking…</div></div>}
        <div ref={bottomRef} />
      </div>
      <div className="p-4 bg-black/20 border-t border-white/10"><div className="flex gap-2"><input type="text" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void handleSend(); }} placeholder="Ask about your documents..." className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 text-neutral-200" /><button onClick={() => void handleSend()} disabled={!input.trim() || loading} className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl disabled:opacity-50">Send</button></div></div>
    </div>
  );
}
