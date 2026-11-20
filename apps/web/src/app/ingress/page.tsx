"use client";

import { useState } from "react";
import { INGRESS_INTERVAL_OPTIONS } from "@/features/ingress/domain/referentials/ingress.referentials";
import { formatIntervalLabel, getStatusColor } from "@/features/ingress/domain/ingress.service";
import { IngressIntervalMinutes } from "@/features/ingress/domain/ingress.model";
import { useIngress } from "@/features/ingress/infrastructure/hooks/useIngress";
import { formatDate } from "@/features/transactions/domain/transaction.service";

export default function IngressPage() {
  const {
    config,
    status,
    loading,
    syncing,
    error,
    notice,
    refresh,
    updateConfig,
    triggerSync,
  } = useIngress();

  const [saving, setSaving] = useState(false);

  const handleToggleEnabled = async () => {
    if (!config) return;
    setSaving(true);
    try {
      await updateConfig({ isEnabled: !config.isEnabled });
    } finally {
      setSaving(false);
    }
  };

  const handleIntervalChange = async (newInterval: number) => {
    if (!config) return;
    setSaving(true);
    try {
      await updateConfig({ intervalMinutes: newInterval as IngressIntervalMinutes });
    } finally {
      setSaving(false);
    }
  };

  const formatTimestamp = (ts: string | null | undefined) => {
    if (!ts) return "Never";
    try {
      const d = new Date(ts);
      return `${formatDate(ts)} ${d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
    } catch {
      return ts;
    }
  };

  const statusColor = config ? getStatusColor(config.status) : "idle";

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem" }}>
        <div>
          <h1 style={{ fontSize: "1.75rem", fontWeight: 700 }}>Ingress Controls & Status</h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
            Autonomous Gmail polling daemon and synchronization cron
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem" }}>
          <button
            onClick={() => triggerSync()}
            disabled={syncing || loading}
            className="btn btn-primary"
            aria-label="Trigger immediate Gmail synchronization"
          >
            {syncing ? "Triggering..." : "⚡ Sync Now"}
          </button>
          <button
            onClick={() => refresh()}
            disabled={loading}
            className="btn btn-secondary"
            aria-label="Refresh ingress status"
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

      {/* Grid of status cards */}
      <div className="grid-stats">
        <div className="card">
          <div className="card-title">Service State</div>
          <div className="card-value">
            <span
              className={`badge badge-${
                statusColor === "running" ? "warning" : statusColor === "error" ? "danger" : "success"
              }`}
            >
              {config?.status || "Idle"}
            </span>
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Provider: {config?.provider || "gmail"}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Automated Sync</div>
          <div className="card-value">
            {config?.isEnabled ? (
              <span style={{ color: "var(--accent-green)" }}>Active</span>
            ) : (
              <span style={{ color: "var(--text-muted)" }}>Paused</span>
            )}
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            {config ? formatIntervalLabel(config.intervalMinutes) : "-"}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Total Emails Processed</div>
          <div className="card-value blue">
            {status?.totalProcessed ?? 0}
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Checkpoint: {status?.lastHistoryId ? `History ID ${status.lastHistoryId}` : "None"}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Next Scheduled Run</div>
          <div className="card-value" style={{ fontSize: "1.125rem" }}>
            {formatTimestamp(config?.nextRunAt)}
          </div>
          <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "0.5rem" }}>
            Last run: {formatTimestamp(config?.lastRunAt)}
          </div>
        </div>
      </div>

      {/* Controls & Configuration */}
      <section className="card" style={{ marginBottom: "1.5rem" }} aria-labelledby="ingress-config-heading">
        <h2 id="ingress-config-heading" style={{ fontSize: "1.125rem", fontWeight: 600, marginBottom: "1rem" }}>
          Schedule Configuration
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", maxWidth: "480px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 600 }}>Automated Polling</div>
              <div style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                Enable or disable automated recurring inbox checks
              </div>
            </div>
            <button
              onClick={handleToggleEnabled}
              disabled={saving || !config}
              className={`btn ${config?.isEnabled ? "btn-secondary" : "btn-primary"}`}
              aria-label="Toggle automated polling"
            >
              {config?.isEnabled ? "Pause Polling" : "Enable Polling"}
            </button>
          </div>

          <div className="form-group">
            <label htmlFor="sync-interval" className="form-label">
              Polling Frequency
            </label>
            <select
              id="sync-interval"
              className="form-select"
              value={config?.intervalMinutes || 60}
              onChange={(e) => handleIntervalChange(Number(e.target.value))}
              disabled={saving || !config}
            >
              {INGRESS_INTERVAL_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Diagnostic & Error Log */}
      {config?.lastError && (
        <section className="card" style={{ borderLeft: "4px solid var(--accent-red)" }} aria-labelledby="error-heading">
          <h2 id="error-heading" style={{ fontSize: "1rem", fontWeight: 600, color: "var(--accent-red)", marginBottom: "0.5rem" }}>
            Last Ingress Diagnostic Error
          </h2>
          <pre
            tabIndex={0}
            style={{
              padding: "0.75rem",
              background: "var(--bg-primary)",
              borderRadius: "var(--radius-sm)",
              fontSize: "0.8125rem",
              overflowX: "auto",
              color: "var(--badge-red-text)",
            }}
          >
            {config.lastError}
          </pre>
        </section>
      )}
    </div>
  );
}
