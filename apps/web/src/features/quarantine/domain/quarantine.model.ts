import { Transaction } from "@/features/transactions/domain/transaction.model";

export interface QuarantineItem {
  transaction: Transaction;
  suggestedCategoryId?: number | null;
}

export interface QuarantineResolution {
  transactionId: number;
  categoryId: number;
  vendorRaw?: string;
}

export interface ReEvaluateResult {
  evaluatedCount: number;
  autoCategorizedCount: number;
}
