import type { Transaction } from "@/features/transactions/domain/transaction.model";

export function filterNeedsReview(transactions: Transaction[]): Transaction[] {
  return transactions.filter(
    (tx) => tx.status === "needs_review" || tx.status === "parsed" || tx.categoryId === null
  );
}

export function sortQuarantineByDate(transactions: Transaction[]): Transaction[] {
  return [...transactions].sort((a, b) => {
    return new Date(b.recordDate).getTime() - new Date(a.recordDate).getTime();
  });
}
