import type { ChatMessage, ChatResponse } from "./chat.model";

export function createMessage(sender: "user" | "assistant", text: string): ChatMessage {
  return {
    id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    sender,
    text,
    timestamp: new Date().toISOString(),
  };
}

export function fromAssistantResponse(res: ChatResponse): ChatMessage {
  return {
    id: `msg-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`,
    sender: "assistant",
    text: res.reply,
    timestamp: new Date().toISOString(),
    actionsExecuted: res.actionsExecuted,
    widgets: res.widgets,
  };
}

export function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return "";
    const formatted = d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    if (formatted === "Invalid Date") return "";
    return formatted;
  } catch {
    return "";
  }
}
