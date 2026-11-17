import {
  IngressConfig,
  IngressStatus,
  IngressTriggerResult,
  UpdateIngressConfigInput,
} from "./ingress.model";

export interface IngressRepository {
  getConfig(provider?: string, token?: string): Promise<IngressConfig>;
  updateConfig(input: UpdateIngressConfigInput, token?: string): Promise<IngressConfig>;
  triggerSync(provider?: string, token?: string): Promise<IngressTriggerResult>;
  getStatus(provider?: string, token?: string): Promise<IngressStatus>;
}
