import { ChatResponse } from "./chat.model";

export interface ChatRepository {
  sendMessage(message: string, token?: string): Promise<ChatResponse>;
}
