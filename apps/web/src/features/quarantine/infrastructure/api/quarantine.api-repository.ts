import { Transaction } from "@/features/transactions/domain/transaction.model";
import {
  BackendTransactionDto,
  toDomainTransaction,
} from "@/features/transactions/infrastructure/mappers/transaction.mapper";
import { HttpClient, defaultHttpClient } from "@/shared/infrastructure/http-client";
import { QuarantineResolution, ReEvaluateResult } from "../../domain/quarantine.model";
import { QuarantineRepository } from "../../domain/quarantine.repository";

interface BackendReEvaluateDto {
  evaluated_count: number;
  auto_categorized_count: number;
}

export class ApiQuarantineRepository implements QuarantineRepository {
  constructor(private readonly http: HttpClient = defaultHttpClient) {}

  async listQuarantined(limit: number = 50, offset: number = 0, token?: string): Promise<Transaction[]> {
    const data = await this.http.get<BackendTransactionDto[]>("/transactions", {
      params: { status: "needs_review", limit, offset },
      token,
    });
    return (data || []).map(toDomainTransaction);
  }

  async resolve(resolution: QuarantineResolution, token?: string): Promise<Transaction> {
    const payload: Record<string, unknown> = {
      category_id: resolution.categoryId,
      status: "categorized",
    };
    if (resolution.vendorRaw) {
      payload.vendor_raw = resolution.vendorRaw;
    }
    const data = await this.http.patch<BackendTransactionDto>(
      `/transactions/${resolution.transactionId}`,
      payload,
      { token }
    );
    return toDomainTransaction(data);
  }

  async dismiss(transactionId: number, token?: string): Promise<void> {
    await this.http.delete(`/transactions/${transactionId}`, { token });
  }

  async reEvaluateAll(token?: string): Promise<ReEvaluateResult> {
    const data = await this.http.post<BackendReEvaluateDto>("/ingestion/re-evaluate", null, {
      token,
    });
    return {
      evaluatedCount: data.evaluated_count,
      autoCategorizedCount: data.auto_categorized_count,
    };
  }
}

export const defaultQuarantineRepository = new ApiQuarantineRepository();
