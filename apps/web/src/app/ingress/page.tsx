"use client";

import { useState } from "react";
import { INGRESS_INTERVAL_OPTIONS } from "@/features/ingress/domain/referentials/ingress.referentials";
import { formatIntervalLabel } from "@/features/ingress/domain/ingress.service";
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

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Ingress Controls & Status</h1>
          <p className="page-subtitle">
            Autonomous Gmail polling daemon and synchronization cron
          </p>
        </div>
        <div style={{ display: "flex", gap: "var(--space-md)" }}>
          <button
            onClick={() => triggerSync()}
            disabled={syncing || loading}
            className="btn btn-primary btn-sm"
            aria-label="Trigger immediate Gmail synchronization"
          >
            {syncing ? "Triggering..." : "Sync Now"}
          </button>
          <button
            onClick={() => refresh()}
            disabled={loading}
            className="btn btn-secondary btn-sm"
            aria-label="Refresh ingress status"
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

      {/* Grid of status cards */}
      <div className="grid-stats">
        <div className="card">
          <div className="card-title">Service State</div>
          <div className="card-value" style={{ fontSize: "var(--font-heading-md-size)" }}>
            {config?.status || "Idle"}
          </div>
          <div style={{ fontSize: "var(--font-caption-size)", color: "var(--text-dark-muted)", marginTop: "var(--space-sm)" }}>
            Provider: {config?.provider || "gmail"}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Automated Sync</div>
          <div className="card-value" style={{ fontSize: "var(--font-heading-md-size)" }}>
            {config?.isEnabled ? "Active" : "Paused"}
          </div>
          <div style={{ fontSize: "var(--font-caption-size)", color: "var(--text-dark-muted)", marginTop: "var(--space-sm)" }}>
            {config ? formatIntervalLabel(config.intervalMinutes) : "-"}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Total Emails Processed</div>
          <div className="card-value">
            {status?.totalProcessed ?? 0}
          </div>
          <div style={{ fontSize: "var(--font-caption-size)", color: "var(--text-dark-muted)", marginTop: "var(--space-sm)" }}>
            Checkpoint: {status?.lastHistoryId ? `History ID ${status.lastHistoryId}` : "None"}
          </div>
        </div>

        <div className="card">
          <div className="card-title">Next Scheduled Run</div>
          <div className="card-value" style={{ fontSize: "var(--font-heading-sm-size)" }}>
            {formatTimestamp(config?.nextRunAt)}
          </div>
          <div style={{ fontSize: "var(--font-caption-size)", color: "var(--text-dark-muted)", marginTop: "var(--space-sm)" }}>
            Last Run: {formatTimestamp(status?.lastRunAt)}
          </div>
        </div>
      </div>

      {/* Ingress Configuration Controls */}
      <section className="card" style={{ marginBottom: "var(--space-xl)" }} aria-labelledby="ingress-config-heading">
        <h2 id="ingress-config-heading" style={{ fontSize: "var(--font-heading-sm-size)", fontWeight: 500, letterSpacing: "-0.44px", marginBottom: "var(--space-base)", color: "var(--canvas)" }}>
          Daemon Execution Settings
        </h2>
        <div style={{ display: "flex", gap: "var(--space-xl)", flexWrap: "wrap", alignItems: "center" }}>
          <div>
            <label className="form-label" style={{ display: "block", marginBottom: "var(--space-xs)" }}>Polling Interval</label>
            <select
              aria-label="Polling Interval"
              className="form-select"
              value={config?.intervalMinutes ?? 15}
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

          <div>
            <label className="form-label" style={{ display: "block", marginBottom: "var(--space-xs)" }}>Daemon Execution</label>
            <button
              onClick={handleToggleEnabled}
              disabled={saving || !config}
              className="btn btn-primary btn-sm"
              aria-label="Toggle autonomous ingress execution"
            >
              {saving ? "Updating..." : config?.isEnabled ? "Pause Daemon" : "Resume Daemon"}
            </button>
          </div>
        </div>
      </section>

      {/* Sync Diagnostics / History */}
      {status?.lastError && (
        <section aria-labelledby="ingress-error-heading" className="alert-box">
          <h2 id="ingress-error-heading" style={{ fontWeight: 500, marginBottom: "var(--space-xs)" }}>
            Last Ingestion Error Encountered
          </h2>
          <pre style={{ overflowX: "auto", fontSize: "12px", color: "var(--ink-muted)", marginTop: "var(--space-xs)" }}>
            {status.lastError}
          </pre>
        </section>
      )}
    </div>
  );
}
