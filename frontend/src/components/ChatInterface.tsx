"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

type Citation = { metadata?: { filename?: string } };
type Message = { role: "user" | "assistant"; content: string; citations?: Citation[] };
type ChatResponse = {
  answer?: string;
  evidence?: Citation[];
  conversation_id?: string | null;
  run_id?: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { role: "user", content: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-User-Id": "demo-user",
        },
        body: JSON.stringify({
          query: userMsg.content,
          conversation_id: conversationId,
        }),
      });

      const data = (await res.json()) as ChatResponse;
      if (!res.ok) throw new Error(data.answer || "Chat request failed");

      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer || "No answer returned.",
          citations: data.evidence,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            error instanceof Error
              ? `Error: ${error.message}`
              : "Error: Could not reach the server.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-neutral-800/50 backdrop-blur-xl border border-white/10 rounded-2xl h-full flex flex-col overflow-hidden">
      <div className="p-4 border-b border-white/10 bg-black/20">
        <h2 className="font-medium text-neutral-200">Intelligence Chat</h2>
        {conversationId && (
          <p className="mt-1 text-xs text-neutral-500">
            Conversation persisted
          </p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        {messages.length === 0 ? (
          <div className="text-center text-neutral-500 h-full flex items-center justify-center">
            Ask any question about your uploaded documents.
          </div>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl p-4 ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white"
                    : "bg-white/5 border border-white/10 text-neutral-200"
                }`}
              >
                {msg.role === "user" ? (
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="prose prose-invert max-w-none prose-sm sm:prose-base">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                )}

                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-3 pt-3 border-t border-white/10">
                    <p className="text-xs text-neutral-400 mb-2 uppercase">
                      Sources
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {msg.citations.map((cit, idx) => (
                        <span
                          key={idx}
                          className="text-xs px-2 py-1 bg-black/30 rounded text-neutral-300 border border-white/5"
                        >
                          {cit.metadata?.filename || "Document"}
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
            <div className="bg-white/5 border border-white/10 rounded-2xl p-4 text-neutral-400">
              Thinking…
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
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about your documents..."
            className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-indigo-500 text-neutral-200"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3 rounded-xl disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
