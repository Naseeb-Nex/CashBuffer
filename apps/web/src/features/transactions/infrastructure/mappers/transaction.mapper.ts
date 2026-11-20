import type {
  Category,
  CreateTransactionInput,
  FinancialSummary,
  Transaction,
  UpdateTransactionInput,
} from "../../domain/transaction.model";

export interface BackendTransactionDto {
  id: number;
  user_id: string;
  amount: number;
  currency: string;
  is_inflow: boolean;
  record_date: string;
  vendor_raw: string;
  category_id: number | null;
  status: "parsed" | "needs_review" | "categorized";
}

export interface BackendCategoryBreakdownItemDto {
  category_id: number | null;
  category_name: string;
  total_amount: number;
}

export interface BackendFinancialSummaryDto {
  total_inflow: number;
  total_outflow: number;
  net_buffer: number;
  transaction_count: number;
  uncategorized_count: number;
  category_breakdown: BackendCategoryBreakdownItemDto[];
  linked_accounts_count: number;
}

export interface BackendCategoryDto {
  id: number;
  user_id: string;
  name: string;
  parent_id: number | null;
}

export function toDomainTransaction(dto: BackendTransactionDto): Transaction {
  return {
    id: dto.id,
    userId: dto.user_id,
    amount: dto.amount,
    currency: dto.currency || "INR",
    isInflow: Boolean(dto.is_inflow),
    recordDate: dto.record_date,
    vendorRaw: dto.vendor_raw || "Unknown",
    categoryId: dto.category_id,
    status: dto.status,
  };
}

export function toDomainFinancialSummary(dto: BackendFinancialSummaryDto): FinancialSummary {
  return {
    totalInflow: dto.total_inflow,
    totalOutflow: dto.total_outflow,
    netBuffer: dto.net_buffer,
    transactionCount: dto.transaction_count,
    uncategorizedCount: dto.uncategorized_count,
    categoryBreakdown: (dto.category_breakdown || []).map((b) => ({
      categoryId: b.category_id,
      categoryName: b.category_name,
      totalAmount: b.total_amount,
    })),
    linkedAccountsCount: dto.linked_accounts_count,
  };
}

export function toDomainCategory(dto: BackendCategoryDto): Category {
  return {
    id: dto.id,
    userId: dto.user_id,
    name: dto.name,
    parentId: dto.parent_id,
  };
}

export function toBackendUpdatePayload(input: UpdateTransactionInput): Record<string, unknown> {
  const payload: Record<string, unknown> = {};
  if (input.categoryId !== undefined) payload.category_id = input.categoryId;
  if (input.status !== undefined) payload.status = input.status;
  if (input.vendorRaw !== undefined) payload.vendor_raw = input.vendorRaw;
  if (input.amount !== undefined) payload.amount = input.amount;
  return payload;
}

export function toBackendCreatePayload(input: CreateTransactionInput): Record<string, unknown> {
  return {
    amount: input.amount,
    vendor_raw: input.vendorRaw,
    currency: input.currency || "INR",
    is_inflow: Boolean(input.isInflow),
    record_date: input.recordDate || new Date().toISOString().split("T")[0],
    category_id: input.categoryId ?? null,
    auto_categorize: input.autoCategorize ?? true,
  };
}
