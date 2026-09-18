import React, { useEffect, useRef, useState } from "react";
import api from "../utils/api";
import toast from "react-hot-toast";

export default function Chatbot() {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi! I'm the NumeriX Assistant. Ask me about any of the methods in this app — root finding, interpolation, integration, ODEs, linear systems, and more.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const scrollRef = useRef(null);

  useEffect(() => {
    api
      .get("/api/chatbot/suggestions")
      .then(({ data }) => setSuggestions(data.suggestions || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text) => {
    const content = (text ?? input).trim();
    if (!content || loading) return;

    const history = messages
      .filter((m) => m.role === "user" || m.role === "assistant")
      .slice(1); // drop the initial greeting from history sent to the model

    const nextMessages = [...messages, { role: "user", content }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const { data } = await api.post("/api/chatbot/ask", {
        message: content,
        history,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.reply, sources: data.sources },
      ]);
    } catch (e) {
      const detail = e.response?.data?.detail || "Something went wrong talking to the assistant.";
      toast.error(detail);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `⚠ ${detail}` },
      ]);
    }
    setLoading(false);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-3xl mx-auto">
      <div className="mb-4">
        <h2 className="section-title">AI Assistant</h2>
        <p className="text-sm text-slate-500 mt-1">
          Retrieval-grounded chat over NumeriX's methods · powered by Gemini
        </p>
      </div>

      <div
        ref={scrollRef}
        className="glass-card flex-1 overflow-y-auto p-4 md:p-6 space-y-4"
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"} animate-fade-up`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                m.role === "user"
                  ? "bg-neon-cyan/10 border border-neon-cyan/30 text-slate-100"
                  : "bg-dark-800 border border-white/5 text-slate-300"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>
              {m.sources && m.sources.length > 0 && (
                <div className="mt-2 pt-2 border-t border-white/5 flex flex-wrap gap-1.5">
                  {m.sources.map((s, j) => (
                    <span
                      key={j}
                      className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-neon-purple/10 text-neon-purple/80 border border-neon-purple/20"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-dark-800 border border-white/5 rounded-2xl px-4 py-3 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse" />
              <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse [animation-delay:150ms]" />
              <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse [animation-delay:300ms]" />
            </div>
          </div>
        )}
      </div>

      {messages.length <= 1 && suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => send(s)}
              className="text-xs font-mono px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-slate-400 hover:text-neon-cyan hover:border-neon-cyan/30 transition-colors"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="mt-4 flex items-end gap-3">
        <textarea
          rows={1}
          className="input-field resize-none"
          placeholder="Ask about a method, e.g. 'How does Newton-Raphson converge?'"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button
          className="btn-primary shrink-0"
          onClick={() => send()}
          disabled={loading || !input.trim()}
        >
          Send
        </button>
      </div>
    </div>
  );
}
