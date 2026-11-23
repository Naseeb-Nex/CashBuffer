"use client";

import { useState } from "react";
import {
  formatCurrency,
  formatDate,
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
      <div className="page-header">
        <div>
          <h1 className="page-title">Expenses Dashboard</h1>
          <p className="page-subtitle">
            Household cash-flow tracking and categorization
          </p>
        </div>
        <button onClick={() => refresh()} className="btn btn-secondary btn-sm" aria-label="Refresh financial data">
          Refresh
        </button>
      </div>

      {error && (
        <div role="alert" className="alert-box">
          {error}
        </div>
      )}

      {/* KPI Cards */}
      <section aria-labelledby="summary-heading">
        <h2 id="summary-heading" className="sr-only">Financial Summary</h2>
        <div className="grid-stats">
          <div className="card">
            <div className="card-title">Net Cash Buffer</div>
            <div className="card-value">
              {summary ? formatCurrency(summary.netBuffer) : "-"}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Total Inflow</div>
            <div className="card-value">
              {summary ? formatCurrency(summary.totalInflow) : "-"}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Total Outflow</div>
            <div className="card-value">
              {summary ? formatCurrency(summary.totalOutflow) : "-"}
            </div>
          </div>
          <div className="card">
            <div className="card-title">Needs Review / Quarantined</div>
            <div className="card-value">
              {summary ? summary.uncategorizedCount : "-"}
            </div>
          </div>
        </div>
      </section>

      {/* Quick Ingest Form */}
      <section className="card" style={{ marginBottom: "var(--space-xl)" }} aria-labelledby="add-tx-heading">
        <h2 id="add-tx-heading" style={{ fontSize: "var(--font-heading-sm-size)", fontWeight: 500, letterSpacing: "-0.44px", marginBottom: "var(--space-md)", color: "var(--canvas)" }}>
          Quick Direct Ingestion
        </h2>
        {formError && (
          <div role="alert" style={{ color: "var(--canvas)", fontSize: "var(--font-caption-size)", marginBottom: "var(--space-sm)", opacity: 0.85 }}>
            {formError}
          </div>
        )}
        <form onSubmit={handleAddTransaction} style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap", alignItems: "flex-end" }}>
          <div className="form-group" style={{ flex: "2", minWidth: "200px", marginBottom: 0 }}>
            <label htmlFor="tx-vendor" className="form-label">Vendor / Narration</label>
            <input
              id="tx-vendor"
              type="text"
              placeholder="e.g. Swiggy, Netflix, Salary"
              className="form-input"
              value={vendorInput}
              onChange={(e) => setVendorInput(e.target.value)}
              required
            />
          </div>
          <div className="form-group" style={{ flex: "1", minWidth: "130px", marginBottom: 0 }}>
            <label htmlFor="tx-amount" className="form-label">Amount (INR)</label>
            <input
              id="tx-amount"
              type="number"
              step="0.01"
              min="0.01"
              placeholder="0.00"
              className="form-input"
              value={amountInput}
              onChange={(e) => setAmountInput(e.target.value)}
              required
            />
          </div>
          <div className="form-group" style={{ marginBottom: 0, justifyContent: "center" }}>
            <label className="form-label" style={{ display: "flex", alignItems: "center", gap: "var(--space-xs)", cursor: "pointer", height: "42px" }}>
              <input
                type="checkbox"
                checked={isInflowInput}
                onChange={(e) => setIsInflowInput(e.target.checked)}
              />
              <span>Inflow (Income)</span>
            </label>
          </div>
          <button type="submit" disabled={submitting} className="btn btn-primary btn-sm" style={{ height: "42px" }}>
            {submitting ? "Ingesting..." : "Record Transaction"}
          </button>
        </form>
      </section>

      {/* Filter Bar */}
      <section style={{ display: "flex", gap: "var(--space-md)", flexWrap: "wrap", alignItems: "center", marginBottom: "var(--space-md)" }} aria-label="Transaction Filters">
        <input
          type="search"
          aria-label="Search transactions"
          placeholder="Search vendor..."
          className="filter-input"
          style={{ maxWidth: "260px" }}
          value={filter.search || ""}
          onChange={(e) => setFilter((prev) => ({ ...prev, search: e.target.value }))}
        />
        <select
          aria-label="Filter by status"
          className="filter-input"
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
            <option key={opt.value} value={opt.value} style={{ background: "#000", color: "#fff" }}>{opt.label}</option>
          ))}
        </select>
        <span aria-live="polite" style={{ color: "var(--ink-muted)", fontSize: "var(--font-caption-size)", marginLeft: "auto" }}>
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
                <td colSpan={5} style={{ textAlign: "center", padding: "2rem", color: "var(--text-dark-muted)" }}>
                  {loading ? "Fetching transactions from server..." : "No transactions found"}
                </td>
              </tr>
            ) : (
              transactions.map((tx) => {
                const category = categories.find((c) => c.id === tx.categoryId);
                return (
                  <tr key={tx.id}>
                    <td>{formatDate(tx.recordDate)}</td>
                    <td style={{ fontWeight: 500 }}>{tx.vendorRaw}</td>
                    <td>{category ? category.name : <span style={{ color: "var(--text-dark-muted)" }}>Unassigned</span>}</td>
                    <td>
                      <span className="badge">
                        {tx.status}
                      </span>
                    </td>
                    <td style={{ textAlign: "right", fontWeight: 500 }}>
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
