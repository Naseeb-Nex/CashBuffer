import type { IngressConfig, IngressIntervalMinutes, IngressStatus } from "./ingress.model";

export function formatIntervalLabel(minutes: number): string {
  switch (minutes) {
    case 15:
      return "Every 15 minutes";
    case 30:
      return "Every 30 minutes";
    case 60:
      return "Every 1 hour";
    case 360:
      return "Every 6 hours";
    case 1440:
      return "Once a day";
    default:
      return `Every ${minutes} minutes`;
  }
}

export function formatPresetIntervalLabel(minutes: number): string {
  switch (minutes) {
    case 15:
      return "15 minutes";
    case 30:
      return "30 minutes";
    case 60:
      return "1 hour";
    case 360:
      return "6 hours";
    case 1440:
      return "1 day";
    default:
      return `${minutes} minutes`;
  }
}

export function isValidInterval(val: number): val is IngressIntervalMinutes {
  return [15, 30, 60, 360, 1440].includes(val);
}

export function getStatusColor(status: string): "idle" | "running" | "error" | "disabled" {
  if (status === "running") return "running";
  if (status === "error" || status === "failed") return "error";
  if (status === "disabled") return "disabled";
  return "idle";
}

export type ConnectionStateKey = "connected" | "not_set_up" | "error";

export interface EmailConnectionInfo {
  state: ConnectionStateKey;
  label: string;
  badgeClass: string;
  message: string;
}

export function sanitizeErrorMessage(rawError: unknown): string {
  if (!rawError) return "An unexpected error occurred.";
  const msg = typeof rawError === "string" ? rawError : (rawError as { message?: string }).message || String(rawError);

  // Strip file paths, stack traces, JSON secrets
  if (msg.includes("/") || msg.includes("\\") || msg.includes("Traceback") || msg.includes("token")) {
    if (msg.toLowerCase().includes("auth") || msg.toLowerCase().includes("unauthorized") || msg.includes("401")) {
      return "Authentication failed. Please check server configuration.";
    }
    if (msg.toLowerCase().includes("timeout") || msg.toLowerCase().includes("timed out")) {
      return "Connection timed out while checking email. Please try again.";
    }
    return "Failed to complete email check. Please try again later.";
  }

  if (msg.toLowerCase().includes("failed to fetch") || msg.toLowerCase().includes("networkerror")) {
    return "Unable to reach the server. Please check your connection.";
  }

  return msg;
}

export function getEmailConnectionStatus(
  status: IngressStatus | IngressConfig | null | undefined
): EmailConnectionInfo {
  if (!status) {
    return {
      state: "not_set_up",
      label: "Not set up",
      badgeClass: "badge-dark",
      message: "Email access is configured on the server for now.",
    };
  }

  if (status.lastError || status.status === "error" || status.status === "failed") {
    return {
      state: "error",
      label: "Needs attention",
      badgeClass: "badge-danger",
      message: sanitizeErrorMessage(status.lastError || "Email connection reported an error."),
    };
  }

  // Active or connected state
  const hasProcessed = "totalProcessed" in status && (status.totalProcessed ?? 0) > 0;
  if (status.status === "running" || hasProcessed || status.lastRunAt) {
    return {
      state: "connected",
      label: "Connected",
      badgeClass: "badge-success",
      message: "Email access is configured on the server for now.",
    };
  }

  return {
    state: "not_set_up",
    label: "Not set up",
    badgeClass: "badge-dark",
    message: "Email access is configured on the server for now.",
  };
}

export interface ExecutionBadgeInfo {
  label: "Waiting" | "Checking now..." | "Needs attention";
  badgeClass: string;
}

export function getExecutionStatusBadge(status: string | null | undefined): ExecutionBadgeInfo {
  if (!status) {
    return { label: "Waiting", badgeClass: "badge-dark" };
  }

  const s = status.toLowerCase();
  if (s === "running") {
    return { label: "Checking now...", badgeClass: "badge-info" };
  }
  if (s === "error" || s === "failed") {
    return { label: "Needs attention", badgeClass: "badge-danger" };
  }
  return { label: "Waiting", badgeClass: "badge-dark" };
}

export function formatFriendlyDateTime(dateStr: string | null | undefined): string {
  if (!dateStr) return "Never";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Never";
    
    return d.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return "Never";
  }
}

export function formatFriendlyNextRun(
  dateStr: string | null | undefined,
  isEnabled: boolean
): string {
  if (!isEnabled) {
    return "Paused";
  }
  if (!dateStr) {
    return "Not scheduled";
  }
  return formatFriendlyDateTime(dateStr);
}
