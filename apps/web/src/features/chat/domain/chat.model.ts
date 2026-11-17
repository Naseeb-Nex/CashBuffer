export type MessageSender = "user" | "assistant" | "system";

export interface ChatWidget {
  type: string;
  data: Record<string, unknown>;
}

export interface ChatMessage {
  id: string;
  sender: MessageSender;
  text: string;
  timestamp: string;
  actionsExecuted?: string[];
  widgets?: ChatWidget[];
}

export interface ChatResponse {
  reply: string;
  actionsExecuted: string[];
  widgets: ChatWidget[];
  context: Record<string, unknown>;
}
