"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

const API_URL = "http://127.0.0.1:8001";
const SESSION_KEY = "nexus_hr_session_id";

interface Message {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
}

interface BedrockMessage {
  role: "user" | "assistant";
  content: Array<{ text?: string; toolUse?: unknown; toolResult?: unknown }>;
}

const TOOL_LABELS: Record<string, string> = {
  search_docs: "🔍 Searched documentation",
  create_ticket: "🎫 Created a support ticket",
};

function extractText(msg: BedrockMessage): string | null {
  const text = msg.content.find((c) => c.text)?.text;
  return text ?? null;
}

function toDisplayMessages(bedrockMessages: BedrockMessage[]): Message[] {
  return bedrockMessages
    .filter((m) => m.role === "user" || m.role === "assistant")
    .flatMap((m) => {
      const text = extractText(m);
      if (!text) return [];
      return [{ role: m.role, content: text }];
    });
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    if (!stored) return;
    setSessionId(stored);
    fetch(`${API_URL}/history?session_id=${stored}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.history?.length) {
          setMessages(toDisplayMessages(data.history));
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function startNewConversation() {
    localStorage.removeItem(SESSION_KEY);
    setSessionId(null);
    setMessages([]);
  }

  async function sendMessage() {
    const question = input.trim();
    if (!question || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: sessionId }),
      });
      const data = await res.json();

      if (data.session_id) {
        setSessionId(data.session_id);
        localStorage.setItem(SESSION_KEY, data.session_id);
      }

      const answerText =
        typeof data.answer === "string"
          ? data.answer
          : data.answer?.content?.[0]?.text ?? "No response";

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: answerText, toolsUsed: data.tools_used ?? [] },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: could not reach the API." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-800">Nexus HR Agent</h1>
          <p className="text-sm text-gray-500">Ask questions about company docs</p>
        </div>
        <button
          onClick={startNewConversation}
          className="text-sm text-gray-500 border rounded-lg px-3 py-1.5 hover:bg-gray-100"
        >
          New conversation
        </button>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <p className="text-center text-gray-400 mt-20">
            Ask a question to get started
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}
          >
            {msg.toolsUsed && msg.toolsUsed.length > 0 && (
              <div className="flex gap-2 mb-1">
                {msg.toolsUsed.map((tool) => (
                  <span
                    key={tool}
                    className="text-xs bg-blue-50 text-blue-700 border border-blue-200 rounded-full px-2 py-0.5"
                  >
                    {TOOL_LABELS[tool] ?? tool}
                  </span>
                ))}
              </div>
            )}
            <div
              className={`max-w-2xl px-4 py-3 rounded-2xl text-sm prose prose-sm ${
                msg.role === "user"
                  ? "bg-blue-600 text-white rounded-br-sm prose-invert"
                  : "bg-white border text-gray-800 rounded-bl-sm"
              }`}
            >
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border px-4 py-3 rounded-2xl rounded-bl-sm text-sm text-gray-400">
              Thinking...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="bg-white border-t px-6 py-4">
        <div className="flex gap-3 max-w-4xl mx-auto">
          <label htmlFor="chat-input" className="sr-only">
            Ask a question
          </label>
          <input
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Ask a question..."
            className="flex-1 border rounded-xl px-4 py-2 text-sm text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            className="bg-blue-600 text-white px-5 py-2 rounded-xl text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
