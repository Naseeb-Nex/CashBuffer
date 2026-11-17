export type TransactionStatus = "parsed" | "needs_review" | "categorized";

export interface Transaction {
  id: number;
  userId: string;
  amount: number;
  currency: string;
  isInflow: boolean;
  recordDate: string;
  vendorRaw: string;
  categoryId: number | null;
  status: TransactionStatus;
}

export interface CategoryBreakdownItem {
  categoryId: number | null;
  categoryName: string;
  totalAmount: number;
}

export interface FinancialSummary {
  totalInflow: number;
  totalOutflow: number;
  netBuffer: number;
  transactionCount: number;
  uncategorizedCount: number;
  categoryBreakdown: CategoryBreakdownItem[];
  linkedAccountsCount: number;
}

export interface Category {
  id: number;
  userId: string;
  name: string;
  parentId: number | null;
}

export interface TransactionFilter {
  limit?: number;
  offset?: number;
  status?: TransactionStatus;
  categoryId?: number;
  startDate?: string;
  endDate?: string;
  search?: string;
  minAmount?: number;
  maxAmount?: number;
}

export interface UpdateTransactionInput {
  categoryId?: number | null;
  status?: TransactionStatus;
  vendorRaw?: string;
  amount?: number;
}

export interface CreateTransactionInput {
  amount: number;
  vendorRaw: string;
  currency?: string;
  isInflow?: boolean;
  recordDate?: string;
  categoryId?: number | null;
  autoCategorize?: boolean;
}
