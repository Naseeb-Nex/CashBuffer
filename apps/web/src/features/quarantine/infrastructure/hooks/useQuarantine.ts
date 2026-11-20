"use client";

import { useCallback, useEffect, useState } from "react";
import { Category, Transaction } from "@/features/transactions/domain/transaction.model";
import { defaultTransactionRepository } from "@/features/transactions/infrastructure/api/transaction.api-repository";
import { QuarantineResolution, ReEvaluateResult } from "../../domain/quarantine.model";
import { defaultQuarantineRepository } from "../api/quarantine.api-repository";

export function useQuarantine() {
  const [items, setItems] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionInProgress, setActionInProgress] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [txList, catList] = await Promise.all([
        defaultQuarantineRepository.listQuarantined(),
        defaultTransactionRepository.listCategories(),
      ]);
      setItems(txList);
      setCategories(catList);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load quarantined items");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const resolveItem = async (resolution: QuarantineResolution) => {
    setActionInProgress(true);
    setError(null);
    try {
      await defaultQuarantineRepository.resolve(resolution);
      setItems((prev) => prev.filter((item) => item.id !== resolution.transactionId));
      setNotice(`Transaction #${resolution.transactionId} resolved and categorized.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to resolve item");
    } finally {
      setActionInProgress(false);
    }
  };

  const dismissItem = async (id: number) => {
    setActionInProgress(true);
    setError(null);
    try {
      await defaultQuarantineRepository.dismiss(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      setNotice(`Transaction #${id} dismissed.`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to dismiss item");
    } finally {
      setActionInProgress(false);
    }
  };

  const reEvaluate = async (): Promise<ReEvaluateResult | undefined> => {
    setActionInProgress(true);
    setError(null);
    try {
      const res = await defaultQuarantineRepository.reEvaluateAll();
      setNotice(`Re-evaluation complete: ${res.autoCategorizedCount} items auto-categorized.`);
      await fetchData();
      return res;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to re-evaluate transactions");
    } finally {
      setActionInProgress(false);
    }
  };

  return {
    items,
    categories,
    loading,
    actionInProgress,
    error,
    notice,
    refresh: fetchData,
    resolveItem,
    dismissItem,
    reEvaluate,
  };
}
