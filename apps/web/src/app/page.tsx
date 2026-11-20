"use client";

import { useState } from "react";
import {
  formatCurrency,
  formatDate,
  getStatusBadgeVariant,
  validateTransactionInput,
} from "@/features/transactions/domain/transaction.service";
import { TRANSACTION_STATUS_OPTIONS } from "@/features/transactions/domain/referentials/transaction.referentials";
import { useTransactions } from "@/features/transactions/infrastructure/hooks/useTransactions";
import { TransactionStatus } from "@/features/transactions/domain/transaction.model";

export default function DashboardPage() {
  const {
    transactions,
    summary,
    categories,
    filter,
    setFilter,
    loading,
    error,
    refresh,
    createTransaction,
  } = useTransactions();

  const [vendorInput, setVendorInput] = useState("");
  const [amountInput, setAmountInput] = useState("");
  const [isInflowInput, setIsInflowInput] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleAddTransaction = async (e: React.FormEvent) => {
    e.preventDefault();
    const amountNum = parseFloat(amountInput);
    const err = validateTransactionInput(amountNum, vendorInput);
    if (err) {
      setFormError(err);
      return;
    }

    setFormError(null);
    setSubmitting(true);
    try {
      await createTransaction({
        amount: amountNum,
        vendorRaw: vendorInput.trim(),
        isInflow: isInflowInput,
        currency: "INR",
        autoCategorize: true,
      });
      setVendorInput("");
      setAmountInput("");
      setIsInflowInput(false);
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to create transaction");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Expenses Dashboard</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Household cash flow, buffer metrics, and categorized ledger
          </p>
        </div>
        <button onClick={() => refresh()} className="btn btn-secondary" aria-label="Refresh financial data">
          Refresh Data
        </button>
      </div>

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

      {/* KPI Cards */}
      <section aria-labelledby="summary-heading">
        <h2 id="summary-heading" className="sr-only">Financial Summary</h2>
        <div className="grid-stats">
          <div className="card">
            <div className="card-title">Net Cash Buffer</div>
            <div className={`card-value ${(summary?.netBuffer ?? 0) >= 0 ? "green" : "red"}`}>
              {summary ? formatCurrency(summary.netBuffer) : "-"}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Total Inflow</div>
            <div className="card-value green">
              {summary ? formatCurrency(summary.totalInflow) : "-"}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Total Outflow</div>
            <div className="card-value red">
              {summary ? formatCurrency(summary.totalOutflow) : "-"}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Needs Review / Quarantined</div>
            <div className="card-value amber">
              {summary ? summary.uncategorizedCount : "-"}
            </div>
          </div>
        </div>
      </section>

      {/* Quick Ingest Form */}
      <section className="card" style={{ marginBottom: "1.5rem" }} aria-labelledby="add-tx-heading">
        <h2 id="add-tx-heading" style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "0.75rem" }}>
          Quick Direct Ingestion
        </h2>
        {formError && (
          <div role="alert" style={{ color: "var(--accent-red)", fontSize: "0.875rem", marginBottom: "0.5rem" }}>
            {formError}
          </div>
        )}
        <form onSubmit={handleAddTransaction} style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: "2", minWidth: "200px", marginBottom: 0 }}>
            <label htmlFor="vendor" className="form-label">Vendor / Description</label>
            <input
              id="vendor"
              type="text"
              className="form-input"
              value={vendorInput}
              onChange={(e) => setVendorInput(e.target.value)}
              placeholder="e.g. Swiggy, Netflix, Amazon"
              required
            />
          </div>
          <div className="form-group" style={{ flex: "1", minWidth: "130px", marginBottom: 0 }}>
            <label htmlFor="amount" className="form-label">Amount (INR)</label>
            <input
              id="amount"
              type="number"
              step="0.01"
              min="0.01"
              className="form-input"
              value={amountInput}
              onChange={(e) => setAmountInput(e.target.value)}
              placeholder="0.00"
              required
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0, justifyContent: "center" }}>
            <label className="form-label" style={{ display: "flex", alignItems: "center", gap: "0.5rem", cursor: "pointer", height: "38px" }}>
              <input
                type="checkbox"
                checked={isInflowInput}
                onChange={(e) => setIsInflowInput(e.target.checked)}
              />
              <span>Inflow (Income)</span>
            </label>
          </div>
          <button type="submit" disabled={submitting} className="btn btn-primary" style={{ height: "38px" }}>
            {submitting ? "Ingesting..." : "Record Transaction"}
          </button>
        </form>
      </section>

      {/* Filter Bar */}
      <section style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center", marginBottom: "1rem" }} aria-label="Transaction Filters">
        <input
          type="search"
          aria-label="Search transactions"
          placeholder="Search vendor..."
          className="form-input"
          style={{ maxWidth: "260px" }}
          value={filter.search || ""}
          onChange={(e) => setFilter((prev) => ({ ...prev, search: e.target.value }))}
        />
        <select
          aria-label="Filter by status"
          className="form-select"
          value={filter.status || "all"}
          onChange={(e) => {
            const val = e.target.value;
            setFilter((prev) => ({
              ...prev,
              status: val === "all" ? undefined : (val as TransactionStatus),
            }));
          }}
        >
          {TRANSACTION_STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <span aria-live="polite" style={{ color: "var(--text-muted)", fontSize: "0.875rem", marginLeft: "auto" }}>
          {loading ? "Loading transactions..." : `${transactions.length} records`}
        </span>
      </section>

      {/* Transactions Table */}
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Vendor</th>
              <th scope="col">Category</th>
              <th scope="col">Status</th>
              <th scope="col" style={{ textAlign: "right" }}>Amount</th>
            </tr>
          </thead>
          <tbody>
            {transactions.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
                  {loading ? "Fetching transactions from server..." : "No transactions found"}
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                const category = categories.find((c) => c.id === tx.categoryId);
                const badgeVariant = getStatusBadgeVariant(tx.status);
                return (
                  <tr key={tx.id}>
                    <td>{formatDate(tx.recordDate)}</td>
                    <td style={{ fontWeight: 600 }}>{tx.vendorRaw}</td>
                    <td>{category ? category.name : <span style={{ color: "var(--text-muted)" }}>Unassigned</span>}</td>
                    <td>
                      <span className={`badge badge-${badgeVariant}`}>
                        {tx.status}
                      </span>
                    </td>
                    <td style={{ textAlign: "right", fontWeight: 700, color: tx.isInflow ? "var(--accent-green)" : "inherit" }}>
                      {tx.isInflow ? "+" : "-"}
                      {formatCurrency(tx.amount, tx.currency)}
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
