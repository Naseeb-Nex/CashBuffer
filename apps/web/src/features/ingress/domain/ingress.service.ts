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

const SENSITIVE_PATTERNS = [
  // Stack traces & code lines
  /Traceback \(most recent call last\)/i,
  /\bat\s+[\w$./\\<>]+:\d+:\d+/i,
  /\bFile\s+["'][^"']+["'],\s+line\s+\d+/i,
  // Database / SQL keywords & postgres errors
  /\b(SELECT|INSERT|UPDATE|DELETE)\s+.*\s+(FROM|INTO|SET)\b/i,
  /\b(psycopg|asyncpg|postgres|postgresql|sqlite|mysql)\b/i,
  /\b(relation|column|table)\s+["']?\w+["']?\s+(does not exist|violates|syntax error)/i,
  /\b(duplicate key|unique constraint|foreign key constraint)\b/i,
  /\bpg_advisory_lock\b/i,
  // File paths & system paths
  /(\/|[a-zA-Z]:\\)(var|usr|etc|home|Users|app|tmp|root|node_modules)[/\\].+/i,
  // URLs with credentials or ports
  /https?:\/\/[^:\s]+:[^@\s]+@/i,
  // Secrets, keys, long token hashes
  /\b(sk-[a-zA-Z0-9]{20,}|AIza[0-9A-Za-z-_]{35})\b/,
  /\bey[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}/,
  /\b(password|secret|bearer|private_key)\s*[:=]/i,
  /[a-f0-9]{32,64}/i,
];

export function sanitizeErrorMessage(rawError: unknown): string {
  if (!rawError) return "An unexpected error occurred.";
  const msg =
    typeof rawError === "string"
      ? rawError
      : (rawError as { message?: string }).message || String(rawError);

  const lower = msg.toLowerCase();

  // Authentication & session errors
  if (
    lower.includes("401") ||
    lower.includes("unauthorized") ||
    lower.includes("bearer") ||
    lower.includes("token verification")
  ) {
    return "We could not load your email settings. Please sign in again.";
  }

  // Network / server connection errors
  if (
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("connection refused")
  ) {
    return "Unable to reach the server. Please check your connection.";
  }

  // Timeout errors
  if (lower.includes("timeout") || lower.includes("timed out")) {
    return "Connection timed out while checking email. Please try again.";
  }

  // Check sensitive patterns
  for (const pattern of SENSITIVE_PATTERNS) {
    if (pattern.test(msg)) {
      return "Failed to complete email check. Please try again later.";
    }
  }

  // If long or multiline, treat as potentially sensitive or unformatted
  if (msg.length > 120 || msg.includes("\n")) {
    return "Failed to complete email check. Please try again later.";
  }

  return msg.trim();
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

export function formatFriendlyDateTime(
  dateStr: string | null | undefined,
  timeZone: string = "UTC"
): string {
  if (!dateStr) return "Never";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return "Never";

    return (
      d.toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
        timeZone,
      }) + " UTC"
    );
  } catch {
    return "Never";
  }
}

export function formatFriendlyNextRun(
  dateStr: string | null | undefined,
  isEnabled: boolean,
  timeZone: string = "UTC"
): string {
  if (!isEnabled) {
    return "Paused";
  }
  if (!dateStr) {
    return "Not scheduled";
  }
  return formatFriendlyDateTime(dateStr, timeZone);
}
