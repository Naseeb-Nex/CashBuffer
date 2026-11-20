import type { Transaction, TransactionStatus } from "./transaction.model";

export function formatCurrency(amount: number, currency: string = "INR"): string {
  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: currency || "INR",
      maximumFractionDigits: 2,
    }).format(amount);
  } catch {
    return `${currency} ${amount.toFixed(2)}`;
  }
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return "N/A";
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return dateStr;
  }
}

export function computeNetBuffer(inflow: number, outflow: number): number {
  return Number((inflow - outflow).toFixed(2));
}

export function isQuarantined(tx: Pick<Transaction, "status">): boolean {
  return tx.status === "needs_review" || tx.status === "parsed";
}

export function validateTransactionInput(amount: number, vendor: string): string | null {
  if (isNaN(amount) || amount <= 0) {
    return "Amount must be a positive number";
  }
  if (!vendor || vendor.trim().length === 0) {
    return "Vendor/Description is required";
  }
  return null;
}

export function getStatusBadgeVariant(status: TransactionStatus): "success" | "warning" | "info" {
  switch (status) {
    case "categorized":
      return "success";
    case "needs_review":
      return "warning";
    case "parsed":
      return "info";
  }
}
