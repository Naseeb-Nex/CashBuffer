import { TransactionStatus } from "../transaction.model";

export interface StatusOption {
  value: TransactionStatus | "all";
  label: string;
}

export const TRANSACTION_STATUS_OPTIONS: readonly StatusOption[] = [
  { value: "all", label: "All Statuses" },
  { value: "categorized", label: "Categorized" },
  { value: "needs_review", label: "Needs Review" },
  { value: "parsed", label: "Parsed" },
] as const;

export const DEFAULT_PAGE_LIMIT = 25;
