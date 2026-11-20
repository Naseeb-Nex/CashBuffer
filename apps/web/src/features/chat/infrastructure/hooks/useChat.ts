"use client";

import { useState } from "react";
import { ChatMessage } from "../../domain/chat.model";
import { createMessage, fromAssistantResponse } from "../../domain/chat.service";
import { defaultChatRepository } from "../api/chat.api-repository";

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial-welcome",
      sender: "assistant",
      text: "Hello! I am your CashBuffer AI financial assistant. Ask me about your expense summary, uncategorized transactions, recurring bills, or financial health.",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [sending, setSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (text: string) => {
    if (!text || text.trim() === "") return;
    const userMsg = createMessage("user", text.trim());
    setMessages((prev) => [...prev, userMsg]);
    setSending(true);
    setError(null);

    try {
      const response = await defaultChatRepository.sendMessage(userMsg.text);
      const assistantMsg = fromAssistantResponse(response);
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Failed to get response from assistant";
      setError(errMsg);
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          sender: "assistant",
          text: `⚠️ Error: ${errMsg}`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } finally {
      setSending(false);
    }
  };

  const clearMessages = () => {
    setMessages([
      {
        id: "initial-welcome",
        sender: "assistant",
        text: "Conversation cleared. How can I help you today?",
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  return {
    messages,
    sending,
    error,
    sendMessage,
    clearMessages,
  };
}
