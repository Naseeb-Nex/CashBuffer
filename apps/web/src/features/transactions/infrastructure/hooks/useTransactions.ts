"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Category,
  CreateTransactionInput,
  FinancialSummary,
  Transaction,
  TransactionFilter,
  UpdateTransactionInput,
} from "../../domain/transaction.model";
import { defaultTransactionRepository } from "../api/transaction.api-repository";

export function useTransactions(initialFilter: TransactionFilter = {}) {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<FinancialSummary | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filter, setFilter] = useState<TransactionFilter>(initialFilter);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [txList, summaryData, categoryList] = await Promise.all([
        defaultTransactionRepository.list(filter),
        defaultTransactionRepository.getSummary(),
        defaultTransactionRepository.listCategories(),
      ]);
      setTransactions(txList);
      setSummary(summaryData);
      setCategories(categoryList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load transactions");
    } finally {
      setLoading(false);
    }
  }, [filter]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updateTx = async (id: number, input: UpdateTransactionInput) => {
    try {
      const updated = await defaultTransactionRepository.update(id, input);
      setTransactions((prev) => prev.map((t) => (t.id === id ? updated : t)));
      return updated;
    } catch (err: unknown) {
      throw new Error(err instanceof Error ? err.message : "Update failed");
    }
  };

  const deleteTx = async (id: number) => {
    try {
      await defaultTransactionRepository.delete(id);
      setTransactions((prev) => prev.filter((t) => t.id !== id));
    } catch (err: unknown) {
      throw new Error(err instanceof Error ? err.message : "Delete failed");
    }
  };

  const createTx = async (input: CreateTransactionInput) => {
    try {
      const created = await defaultTransactionRepository.createDirect(input);
      setTransactions((prev) => [created, ...prev]);
      // Refresh summary
      defaultTransactionRepository.getSummary().then(setSummary).catch(() => {});
      return created;
    } catch (err: unknown) {
      throw new Error(err instanceof Error ? err.message : "Creation failed");
    }
  };

  return {
    transactions,
    summary,
    categories,
    filter,
    setFilter,
    loading,
    error,
    refresh: fetchData,
    updateTransaction: updateTx,
    deleteTransaction: deleteTx,
    createTransaction: createTx,
  };
}
