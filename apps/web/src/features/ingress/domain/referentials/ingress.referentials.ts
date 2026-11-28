import { IngressIntervalMinutes } from "../ingress.model";

export interface IntervalOption {
  value: IngressIntervalMinutes;
  label: string;
}

export const INGRESS_INTERVAL_OPTIONS: readonly IntervalOption[] = [
  { value: 15, label: "15 minutes" },
  { value: 30, label: "30 minutes" },
  { value: 60, label: "1 hour" },
  { value: 360, label: "6 hours" },
  { value: 1440, label: "1 day" },
] as const;
