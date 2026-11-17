import type { IngressIntervalMinutes } from "./ingress.model";

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
      return "Once a day (24h)";
    default:
      return `Every ${minutes} minutes`;
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
