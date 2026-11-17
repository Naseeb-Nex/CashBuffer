import type {
  IngressConfig,
  IngressIntervalMinutes,
  IngressStatus,
  IngressTriggerResult,
  UpdateIngressConfigInput,
} from "../../domain/ingress.model";

export interface BackendIngressConfigDto {
  id: string;
  household_id: string;
  user_id: string;
  provider: string;
  is_enabled: boolean;
  interval_minutes: number;
  last_run_at: string | null;
  next_run_at: string | null;
  status: string;
  last_error: string | null;
  created_at: string | null;
}

export interface BackendIngressStatusDto {
  household_id: string;
  provider: string;
  status: string;
  is_enabled: boolean;
  interval_minutes: number;
  last_run_at: string | null;
  next_run_at: string | null;
  last_error: string | null;
  total_processed: number;
  last_history_id: string | null;
  last_email_internal_date: number | null;
  checkpoint_updated_at: string | null;
}

export interface BackendIngressTriggerDto {
  message: string;
  next_run_at: string;
  status: string;
  config: BackendIngressConfigDto;
}

export function toDomainIngressConfig(dto: BackendIngressConfigDto): IngressConfig {
  return {
    id: dto.id,
    householdId: dto.household_id,
    userId: dto.user_id,
    provider: dto.provider,
    isEnabled: dto.is_enabled,
    intervalMinutes: dto.interval_minutes as IngressIntervalMinutes,
    lastRunAt: dto.last_run_at,
    nextRunAt: dto.next_run_at,
    status: dto.status,
    lastError: dto.last_error,
    createdAt: dto.created_at,
  };
}

export function toDomainIngressStatus(dto: BackendIngressStatusDto): IngressStatus {
  return {
    householdId: dto.household_id,
    provider: dto.provider,
    status: dto.status,
    isEnabled: dto.is_enabled,
    intervalMinutes: dto.interval_minutes,
    lastRunAt: dto.last_run_at,
    nextRunAt: dto.next_run_at,
    lastError: dto.last_error,
    totalProcessed: dto.total_processed,
    lastHistoryId: dto.last_history_id,
    lastEmailInternalDate: dto.last_email_internal_date,
    checkpointUpdatedAt: dto.checkpoint_updated_at,
  };
}

export function toDomainIngressTriggerResult(dto: BackendIngressTriggerDto): IngressTriggerResult {
  return {
    message: dto.message,
    nextRunAt: dto.next_run_at,
    status: dto.status,
    config: toDomainIngressConfig(dto.config),
  };
}

export function toBackendUpdateIngressPayload(input: UpdateIngressConfigInput): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    provider: input.provider || "gmail",
  };
  if (input.intervalMinutes !== undefined) {
    payload.interval_minutes = input.intervalMinutes;
  }
  if (input.isEnabled !== undefined) {
    payload.is_enabled = input.isEnabled;
  }
  return payload;
}
