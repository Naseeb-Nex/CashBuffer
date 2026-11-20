export type IngressIntervalMinutes = 15 | 30 | 60 | 360 | 1440;

export interface IngressConfig {
  id: string;
  householdId: string;
  userId: string;
  provider: string;
  isEnabled: boolean;
  intervalMinutes: IngressIntervalMinutes;
  lastRunAt: string | null;
  nextRunAt: string | null;
  status: "idle" | "running" | "error" | string;
  lastError: string | null;
  createdAt: string | null;
}

export interface IngressStatus {
  householdId: string;
  provider: string;
  status: "idle" | "running" | "error" | string;
  isEnabled: boolean;
  intervalMinutes: number;
  lastRunAt: string | null;
  nextRunAt: string | null;
  lastError: string | null;
  totalProcessed: number;
  lastHistoryId: string | null;
  lastEmailInternalDate: number | null;
  checkpointUpdatedAt: string | null;
}

export interface UpdateIngressConfigInput {
  intervalMinutes?: IngressIntervalMinutes;
  isEnabled?: boolean;
  provider?: string;
}

export interface IngressTriggerResult {
  message: string;
  nextRunAt: string;
  status: string;
  config: IngressConfig;
}
