import {
  Category,
  CreateTransactionInput,
  FinancialSummary,
  Transaction,
  TransactionFilter,
  UpdateTransactionInput,
} from "./transaction.model";

export interface TransactionRepository {
  list(filter?: TransactionFilter, token?: string): Promise<Transaction[]>;
  getSummary(token?: string): Promise<FinancialSummary>;
  update(id: number, input: UpdateTransactionInput, token?: string): Promise<Transaction>;
  delete(id: number, token?: string): Promise<void>;
  createDirect(input: CreateTransactionInput, token?: string): Promise<Transaction>;
  listCategories(token?: string): Promise<Category[]>;
}
