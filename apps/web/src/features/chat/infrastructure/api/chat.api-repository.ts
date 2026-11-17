import { HttpClient, defaultHttpClient } from "@/shared/infrastructure/http-client";
import { ChatResponse } from "../../domain/chat.model";
import { ChatRepository } from "../../domain/chat.repository";
import { BackendChatResponseDto, toDomainChatResponse } from "../mappers/chat.mapper";

export class ApiChatRepository implements ChatRepository {
  constructor(private readonly http: HttpClient = defaultHttpClient) {}

  async sendMessage(message: string, token?: string): Promise<ChatResponse> {
    const data = await this.http.post<BackendChatResponseDto>(
      "/assistant/chat",
      { message },
      { token }
    );
    return toDomainChatResponse(data);
  }
}

export const defaultChatRepository = new ApiChatRepository();
