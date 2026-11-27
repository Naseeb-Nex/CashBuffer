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
      <div className="page-header">
        <div>
          <h1 className="page-title">AI Financial Assistant</h1>
          <p className="page-subtitle">
            Natural language interface for your financial insights and expenses
          </p>
        </div>
        <button
          onClick={clearMessages}
          className="btn btn-secondary btn-sm"
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
                <div style={{ marginTop: "var(--space-sm)", display: "flex", flexWrap: "wrap", gap: "var(--space-xs)" }}>
                  {msg.actionsExecuted.map((action, idx) => (
                    <span
                      key={idx}
                      className="badge badge-dark"
                      style={{ fontSize: "11px", padding: "2px 8px" }}
                    >
                      {action}
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
              <span style={{ color: "var(--ink-muted)", fontStyle: "italic" }}>
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
              padding: "var(--space-sm) var(--space-lg)",
              backgroundColor: "transparent",
              color: "var(--ink)",
              fontSize: "var(--font-caption-size)",
              borderTop: "1px solid var(--accent-2)",
            }}
          >
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="chat-input-bar">
          <label htmlFor="chat-input" className="sr-only">
            Message the AI Financial Assistant
          </label>
          <input
            id="chat-input"
            type="text"
            className="filter-input"
            placeholder="Ask e.g. 'What is my buffer balance?' or 'Show my highest expense'"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            disabled={sending}
            autoComplete="off"
            required
          />
          <button
            type="submit"
            className="btn btn-primary btn-sm"
            disabled={sending}
            aria-label="Send message to assistant"
          >
            {sending ? "..." : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
