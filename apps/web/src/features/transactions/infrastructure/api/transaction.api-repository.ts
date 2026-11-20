import { HttpClient, defaultHttpClient } from "@/shared/infrastructure/http-client";
import {
  Category,
  CreateTransactionInput,
  FinancialSummary,
  Transaction,
  TransactionFilter,
  UpdateTransactionInput,
} from "../../domain/transaction.model";
import { TransactionRepository } from "../../domain/transaction.repository";
import {
  BackendCategoryDto,
  BackendFinancialSummaryDto,
  BackendTransactionDto,
  toBackendCreatePayload,
  toBackendUpdatePayload,
  toDomainCategory,
  toDomainFinancialSummary,
  toDomainTransaction,
} from "../mappers/transaction.mapper";

export class ApiTransactionRepository implements TransactionRepository {
  constructor(private readonly http: HttpClient = defaultHttpClient) {}

  async list(filter: TransactionFilter = {}, token?: string): Promise<Transaction[]> {
    const params: Record<string, string | number | boolean | undefined> = {};
    if (filter.limit !== undefined) params.limit = filter.limit;
    if (filter.offset !== undefined) params.offset = filter.offset;
    if (filter.status !== undefined) params.status = filter.status;
    if (filter.categoryId !== undefined) params.category_id = filter.categoryId;
    if (filter.startDate !== undefined) params.start_date = filter.startDate;
    if (filter.endDate !== undefined) params.end_date = filter.endDate;
    if (filter.search !== undefined && filter.search.trim() !== "") params.search = filter.search.trim();
    if (filter.minAmount !== undefined) params.min_amount = filter.minAmount;
    if (filter.maxAmount !== undefined) params.max_amount = filter.maxAmount;

    const data = await this.http.get<BackendTransactionDto[]>("/transactions", {
      params,
      token,
    });
    return (data || []).map(toDomainTransaction);
  }

  async getSummary(token?: string): Promise<FinancialSummary> {
    const data = await this.http.get<BackendFinancialSummaryDto>("/transactions/summary", {
      token,
    });
    return toDomainFinancialSummary(data);
  }

  async update(id: number, input: UpdateTransactionInput, token?: string): Promise<Transaction> {
    const payload = toBackendUpdatePayload(input);
    const data = await this.http.patch<BackendTransactionDto>(`/transactions/${id}`, payload, {
      token,
    });
    return toDomainTransaction(data);
  }

  async delete(id: number, token?: string): Promise<void> {
    await this.http.delete(`/transactions/${id}`, { token });
  }

  async createDirect(input: CreateTransactionInput, token?: string): Promise<Transaction> {
    const payload = toBackendCreatePayload(input);
    const data = await this.http.post<BackendTransactionDto>("/ingestion/direct", payload, {
      token,
    });
    return toDomainTransaction(data);
  }

  async listCategories(token?: string): Promise<Category[]> {
    const data = await this.http.get<BackendCategoryDto[]>("/categories", {
      token,
    });
    return (data || []).map(toDomainCategory);
  }
}

export const defaultTransactionRepository = new ApiTransactionRepository();
