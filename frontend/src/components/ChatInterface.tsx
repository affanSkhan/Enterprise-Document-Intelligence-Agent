"use client";
import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export default function ChatInterface() {
  const [messages, setMessages] = useState<{role: string, content: string, citations?: any[]}[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMsg = { role: 'user', content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const res = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: userMsg.content })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer, citations: data.context }]);
    } catch (error) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error: Could not reach the server.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl h-full flex flex-col overflow-hidden">
      <div className="p-4 border-b border-white/10 flex items-center gap-3 bg-black/20">
        <div className="w-8 h-8 rounded bg-indigo-500/20 flex items-center justify-center">
          <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </div>
        <h2 className="font-medium text-neutral-200">Intelligence Chat</h2>
      </div>
      
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="text-center text-neutral-500 h-full flex items-center justify-center">
            Ask any question about your uploaded documents.
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl p-4 ${msg.role === 'user' ? 'bg-indigo-600 text-white' : 'bg-white/5 border border-white/10 text-neutral-200'}`}>
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="prose prose-invert max-w-none prose-sm sm:prose-base prose-p:leading-relaxed prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/10">
                    <p className="text-xs text-neutral-400 mb-2 font-medium uppercase tracking-wider">Sources</p>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cit, idx) => (
                        <span key={idx} className="text-xs px-2 py-1 bg-black/30 rounded text-neutral-300 border border-white/5">
                          {cit.metadata?.filename}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/5 border border-white/10 rounded-2xl p-4 text-neutral-400 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></div>
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse delay-75"></div>
              <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse delay-150"></div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="p-4 bg-black/20 border-t border-white/10">
        <div className="flex gap-2">
          <input 
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Ask about your documents..."
            className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 transition-colors placeholder-neutral-500 text-neutral-200"
          />
          <button 
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl transition-all disabled:opacity-50 font-medium"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
