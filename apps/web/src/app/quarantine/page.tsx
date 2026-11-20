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
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Quarantine Review</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Transactions requiring verification or categorization confirmation
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            onClick={() => reEvaluate()}
            disabled={actionInProgress}
            className="btn btn-secondary"
            aria-label="Re-evaluate all items against vendor rules"
          >
            Run Rule Engine
          </button>
          <button
            onClick={() => refresh()}
            disabled={loading}
            className="btn btn-secondary"
            aria-label="Refresh quarantine list"
          >
            Refresh
          </button>
        </div>
      </div>

      {notice && (
        <div
          role="status"
          aria-live="polite"
          style={{
            padding: "0.75rem 1rem",
            backgroundColor: "var(--badge-green-bg)",
            color: "var(--badge-green-text)",
            borderRadius: "var(--radius-sm)",
            marginBottom: "1.5rem",
          }}
        >
          {notice}
        </div>
      )}

      {error && (
        <div
          role="alert"
          style={{
            padding: "0.75rem 1rem",
            backgroundColor: "var(--badge-red-bg)",
            color: "var(--badge-red-text)",
            borderRadius: "var(--radius-sm)",
            marginBottom: "1.5rem",
          }}
        >
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
                <td colSpan={5} style={{ textAlign: "center", padding: "2.5rem", color: "var(--text-muted)" }}>
                  {loading ? "Loading quarantined items..." : "🎉 All caught up! Zero items in quarantine review."}
                </td>
              </tr>
            ) : (
              items.map((tx) => {
                const selectedCat = selectedCategories[tx.id] ?? (tx.categoryId || (categories[0] ? categories[0].id : ""));
                return (
                  <tr key={tx.id}>
                    <td>{formatDate(tx.recordDate)}</td>
                    <td style={{ fontWeight: 600 }}>{tx.vendorRaw}</td>
                    <td style={{ fontWeight: 700, color: tx.isInflow ? "var(--accent-green)" : "var(--accent-red)" }}>
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
                      >
                        {categories.map((c) => (
                          <option key={c.id} value={c.id}>
                            {c.name}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div style={{ display: "inline-flex", gap: "0.5rem" }}>
                        <button
                          onClick={() => handleResolve(tx.id)}
                          disabled={actionInProgress}
                          className="btn btn-primary"
                          style={{ padding: "0.35rem 0.75rem", fontSize: "0.8125rem" }}
                          aria-label={`Approve and categorize ${tx.vendorRaw}`}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => dismissItem(tx.id)}
                          disabled={actionInProgress}
                          className="btn btn-danger"
                          style={{ padding: "0.35rem 0.75rem", fontSize: "0.8125rem" }}
                          aria-label={`Dismiss transaction ${tx.vendorRaw}`}
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
