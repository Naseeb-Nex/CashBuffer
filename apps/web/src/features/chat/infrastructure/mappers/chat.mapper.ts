import { ChatResponse, ChatWidget } from "../../domain/chat.model";

export interface BackendChatResponseDto {
  reply: string;
  actions_executed: string[];
  widgets: Array<Record<string, unknown>>;
  context: Record<string, unknown>;
}

export function toDomainChatResponse(dto: BackendChatResponseDto): ChatResponse {
  return {
    reply: dto.reply || "",
    actionsExecuted: dto.actions_executed || [],
    widgets: (dto.widgets || []).map((w) => ({
      type: typeof w.type === "string" ? w.type : "custom",
      data: w,
    })),
    context: dto.context || {},
  };
}
