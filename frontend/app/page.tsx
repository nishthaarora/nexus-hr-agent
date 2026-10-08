"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";

const API_URL = "http://127.0.0.1:8001";
const SESSION_KEY = "nexus_hr_session_id";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "";

interface Message {
  role: "user" | "assistant";
  content: string;
  toolsUsed?: string[];
  isError?: boolean;
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

function extractErrorMessage(data: unknown): string {
  const detail = (data as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && typeof (detail[0] as { msg?: unknown })?.msg === "string") {
    return (detail[0] as { msg: string }).msg;
  }
  return "something went wrong. Please try again.";
}

function friendlyErrorFor(status: number, detail: string): string {
  switch (status) {
    case 401:
      return "You're not authorized to use this assistant.";
    case 413:
      return "This conversation has grown too long for the model. Try starting a new conversation.";
    case 422:
      return detail;
    case 429:
      return "Too many requests right now — please wait a moment and try again.";
    default:
      return "Something went wrong on our end. Please try again.";
  }
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
    fetch(`${API_URL}/history?session_id=${stored}`, {
      headers: { "x-api-key": API_KEY },
    })
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

    let assistantText = ""
    let toolsUsedForTurn: string[]  = [];
    let assistantMessageIndex: number | null = null;

    function upsertAssistantMessage(content: string, isError = false) {
      setMessages((prev) => {
        if (assistantMessageIndex === null) {
          assistantMessageIndex = prev.length;
          return [...prev, { role: "assistant", content, toolsUsed: toolsUsedForTurn, isError }];
        }
        const next = [...prev];
        next[assistantMessageIndex] = { role: "assistant", content, toolsUsed: toolsUsedForTurn, isError };
        return next;
      });
    }

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-api-key": API_KEY },
        body: JSON.stringify({ question, session_id: sessionId }),
      });

      if (!res.ok) {
        // Non-2xx responses aren't guaranteed to have a JSON body — an
        // unhandled backend exception returns a plain-text 500, which
        // would throw if we called res.json() unconditionally.
        let data: unknown = null;
        try {
          data = await res.json();
        } catch {
          // body wasn't JSON (e.g. plain-text 500); fall back below.
        }
        const detail = data ? extractErrorMessage(data) : "Something went wrong on our end. Please try again.";
        setMessages((prev) => [...prev, { role: "assistant", content: friendlyErrorFor(res.status, detail), isError: true }]);
        return;
      }

      if (!res.body) {
        throw new Error("No response body to stream");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE frames are separated by a blank line ("\n\n").
        let frameEnd: number;
        while ((frameEnd = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, frameEnd);
          buffer = buffer.slice(frameEnd + 2);

          let eventName = "message";
          let dataLine = "";
          for (const line of frame.split("\n")) {
            if (line.startsWith("event: ")) eventName = line.slice(7);
            else if (line.startsWith("data: ")) dataLine = line.slice(6);
          }
          if (!dataLine) continue;

          let payload: {
            session_id?: string;
            text?: string;
            tool_name?: string;
            detail?: string;
          };
          try {
            payload = JSON.parse(dataLine);
          } catch {
            continue;
          }

          switch (eventName) {
            case "session_id":
              if (payload.session_id) {
                setSessionId(payload.session_id);
                localStorage.setItem(SESSION_KEY, payload.session_id);
              }
              break;
            case "text_chunk":
              assistantText += payload.text ?? "";
              upsertAssistantMessage(assistantText);
              break;
            case "tool_use":
              if (payload.tool_name && !toolsUsedForTurn.includes(payload.tool_name)) {
                toolsUsedForTurn = [...toolsUsedForTurn, payload.tool_name];
                upsertAssistantMessage(assistantText);
              }
              break;
            case "message_end":
              break;
            case "max_tokens_reached":
            case "rate_limited":
            case "context_too_large":
            case "error":
              upsertAssistantMessage(payload.detail ?? "Something went wrong on our end. Please try again.", true);
              break;
            default:
              break;
          }
        }
      }

      if (assistantMessageIndex === null) {
        // Stream ended without any text_chunk (e.g. a tool-only turn).
        upsertAssistantMessage("No response");
      }
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
                : msg.isError
                ? "bg-red-50 border border-red-200 text-red-700 rounded-bl-sm"
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
