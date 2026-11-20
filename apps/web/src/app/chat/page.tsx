"use client";

import { useEffect, useRef, useState } from "react";
import { formatTime } from "@/features/chat/domain/chat.service";
import { useChat } from "@/features/chat/infrastructure/hooks/useChat";

export default function ChatPage() {
  const { messages, sending, error, sendMessage, clearMessages } = useChat();
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || sending) return;
    sendMessage(inputText);
    setInputText("");
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>AI Financial Assistant</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Natural language interface for your financial insights and expenses
          </p>
        </div>
        <button
          onClick={clearMessages}
          className="btn btn-secondary"
          aria-label="Clear chat conversation"
        >
          Reset Chat
        </button>
      </div>

      <div className="chat-box" role="region" aria-label="AI Chat Session">
        <div className="chat-messages" aria-live="polite">
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-bubble ${msg.sender}`}>
              <div>{msg.text}</div>

              {msg.actionsExecuted && msg.actionsExecuted.length > 0 && (
                <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                  {msg.actionsExecuted.map((action, idx) => (
                    <span
                      key={idx}
                      className="badge badge-info"
                      style={{ fontSize: "0.65rem", padding: "0.1rem 0.4rem" }}
                    >
                      ⚡ {action}
                    </span>
                  ))}
                </div>
              )}

              <div className="chat-bubble-meta">
                <span>{msg.sender === "user" ? "You" : "CashBuffer AI"}</span>
                <span>{formatTime(msg.timestamp)}</span>
              </div>
            </div>
          ))}

          {sending && (
            <div className="chat-bubble assistant" aria-label="Assistant is thinking">
              <span style={{ color: "var(--text-muted)", fontStyle: "italic" }}>
                Analyzing and preparing response...
              </span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {error && (
          <div
            role="alert"
            style={{
              padding: "0.5rem 1rem",
              backgroundColor: "var(--badge-red-bg)",
              color: "var(--badge-red-text)",
              fontSize: "0.8125rem",
              borderTop: "1px solid var(--border)",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="chat-input-bar">
          <label htmlFor="chat-input" className="sr-only" style={{ display: "none" }}>
            Message the AI Financial Assistant
          </label>
          <input
            id="chat-input"
            type="text"
            className="form-input"
            placeholder="Ask e.g. 'What is my buffer balance?' or 'Show my highest expense'"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={sending}
            autoComplete="off"
            required
          />
          <button
            type="submit"
            className="btn btn-primary"
            disabled={sending || !inputText.trim()}
            aria-label="Send message"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}
