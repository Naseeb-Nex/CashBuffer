import { Transaction } from "@/features/transactions/domain/transaction.model";
import { QuarantineResolution, ReEvaluateResult } from "./quarantine.model";

export interface QuarantineRepository {
  listQuarantined(limit?: number, offset?: number, token?: string): Promise<Transaction[]>;
  resolve(resolution: QuarantineResolution, token?: string): Promise<Transaction>;
  dismiss(transactionId: number, token?: string): Promise<void>;
  reEvaluateAll(token?: string): Promise<ReEvaluateResult>;
}
