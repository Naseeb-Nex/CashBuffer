import { HttpClient, defaultHttpClient } from "@/shared/infrastructure/http-client";
import {
  IngressConfig,
  IngressStatus,
  IngressTriggerResult,
  UpdateIngressConfigInput,
} from "../../domain/ingress.model";
import { IngressRepository } from "../../domain/ingress.repository";
import {
  BackendIngressConfigDto,
  BackendIngressStatusDto,
  BackendIngressTriggerDto,
  toBackendUpdateIngressPayload,
  toDomainIngressConfig,
  toDomainIngressStatus,
  toDomainIngressTriggerResult,
} from "../mappers/ingress.mapper";

export class ApiIngressRepository implements IngressRepository {
  constructor(private readonly http: HttpClient = defaultHttpClient) {}

  async getConfig(provider: string = "gmail", token?: string): Promise<IngressConfig> {
    const data = await this.http.get<BackendIngressConfigDto>("/ingress/config", {
      params: { provider },
      token,
    });
    return toDomainIngressConfig(data);
  }

  async updateConfig(input: UpdateIngressConfigInput, token?: string): Promise<IngressConfig> {
    const payload = toBackendUpdateIngressPayload(input);
    const data = await this.http.patch<BackendIngressConfigDto>("/ingress/config", payload, {
      token,
    });
    return toDomainIngressConfig(data);
  }

  async triggerSync(provider: string = "gmail", token?: string): Promise<IngressTriggerResult> {
    const data = await this.http.post<BackendIngressTriggerDto>("/ingress/trigger", null, {
      params: { provider },
      token,
    });
    return toDomainIngressTriggerResult(data);
  }

  async getStatus(provider: string = "gmail", token?: string): Promise<IngressStatus> {
    const data = await this.http.get<BackendIngressStatusDto>("/ingress/status", {
      params: { provider },
      token,
    });
    return toDomainIngressStatus(data);
  }
}

export const defaultIngressRepository = new ApiIngressRepository();
