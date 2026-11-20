"use client";

import { useState } from "react";
import { formatCurrency, formatDate } from "@/features/transactions/domain/transaction.service";
import { useQuarantine } from "@/features/quarantine/infrastructure/hooks/useQuarantine";

export default function QuarantinePage() {
  const {
    items,
    categories,
    loading,
    actionInProgress,
    error,
    notice,
    refresh,
    resolveItem,
    dismissItem,
    reEvaluate,
  } = useQuarantine();

  const [selectedCategories, setSelectedCategories] = useState<Record<number, number>>({});

  const handleCategoryChange = (txId: number, categoryId: number) => {
    setSelectedCategories((prev) => ({ ...prev, [txId]: categoryId }));
  };

  const handleResolve = async (txId: number) => {
    const categoryId = selectedCategories[txId] || (categories[0] ? categories[0].id : null);
    if (!categoryId) {
      alert("Please select a category first");
      return;
    }
    await resolveItem({
      transactionId: txId,
      categoryId,
    });
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Quarantine Review</h1>
          <p className="page-subtitle">
            Transactions requiring verification or categorization confirmation
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-md)" }}>
          <button
            onClick={() => reEvaluate()}
            disabled={actionInProgress}
            className="btn btn-secondary btn-sm"
            aria-label="Re-evaluate all items against vendor rules"
          >
            Run Rule Engine
          </button>
          <button
            onClick={() => refresh()}
            disabled={loading}
            className="btn btn-secondary btn-sm"
            aria-label="Refresh quarantine list"
          >
            Refresh
          </button>
        </div>
      </div>

      {notice && (
        <div role="status" aria-live="polite" className="notice-box">
          {notice}
        </div>
      )}

      {error && (
        <div role="alert" className="alert-box">
          {error}
        </div>
      )}

      {/* Quarantine Table */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Vendor / Description</th>
              <th scope="col">Amount</th>
              <th scope="col">Assign Category</th>
              <th scope="col" style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", padding: "2.5rem", color: "var(--text-dark-muted)" }}>
                  {loading ? "Loading quarantined items..." : "All caught up. Zero items in quarantine review."}
                </td>
              </tr>
            ) : (
              items.map((tx) => {
                const selectedCat = selectedCategories[tx.id] ?? (tx.categoryId || (categories[0] ? categories[0].id : ""));
                return (
                  <tr key={tx.id}>
                    <td>{formatDate(tx.recordDate)}</td>
                    <td style={{ fontWeight: 500 }}>{tx.vendorRaw}</td>
                    <td style={{ fontWeight: 500 }}>
                      {tx.isInflow ? "+" : "-"}
                      {formatCurrency(tx.amount, tx.currency)}
                    </td>
                    <td>
                      <select
                        aria-label={`Assign category for ${tx.vendorRaw}`}
                        className="form-select"
                        value={selectedCat}
                        onChange={(e) => handleCategoryChange(tx.id, Number(e.target.value))}
                        disabled={actionInProgress}
                        style={{ padding: "6px 12px", fontSize: "var(--font-caption-size)" }}
                      >
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "var(--space-sm)" }}>
                        <button
                          onClick={() => handleResolve(tx.id)}
                          disabled={actionInProgress}
                          className="btn btn-primary btn-sm"
                          aria-label={`Approve and categorize ${tx.vendorRaw}`}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => dismissItem(tx.id)}
                          disabled={actionInProgress}
                          className="btn btn-secondary btn-sm"
                          style={{ borderColor: "var(--hairline)", color: "var(--canvas)" }}
                          aria-label={`Dismiss ${tx.vendorRaw}`}
                        >
                          Dismiss
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
