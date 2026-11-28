"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { INGRESS_INTERVAL_OPTIONS } from "@/features/ingress/domain/referentials/ingress.referentials";
import {
  formatFriendlyDateTime,
  formatFriendlyNextRun,
  getEmailConnectionStatus,
  getExecutionStatusBadge,
  sanitizeErrorMessage,
} from "@/features/ingress/domain/ingress.service";
import { IngressIntervalMinutes } from "@/features/ingress/domain/ingress.model";
import { useIngress } from "@/features/ingress/infrastructure/hooks/useIngress";

export default function SettingsPage() {
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

  const [savingSchedule, setSavingSchedule] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [noticeDismissed, setNoticeDismissed] = useState(false);

  const syncingRef = useRef(false);
  const noticeTimerRef = useRef<NodeJS.Timeout | null>(null);

  const clearNoticeTimer = useCallback(() => {
    if (noticeTimerRef.current) {
      clearTimeout(noticeTimerRef.current);
      noticeTimerRef.current = null;
    }
  }, []);

  const showActionNotice = useCallback(
    (msg: string) => {
      clearNoticeTimer();
      setNoticeDismissed(false);
      setActionNotice(msg);
      noticeTimerRef.current = setTimeout(() => {
        setActionNotice(null);
      }, 4000);
    },
    [clearNoticeTimer]
  );

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      clearNoticeTimer();
    };
  }, [clearNoticeTimer]);

  const connectionInfo = getEmailConnectionStatus(status || config);
  const executionBadge = getExecutionStatusBadge(status?.status || config?.status);

  const isEnabled = config?.isEnabled ?? true;
  const intervalMinutes = (config?.intervalMinutes ?? 60) as IngressIntervalMinutes;

  const handleToggleEnabled = async () => {
    if (!config || savingSchedule) return;
    setSavingSchedule(true);
    setActionError(null);
    try {
      const nextState = !isEnabled;
      await updateConfig({ isEnabled: nextState });
      showActionNotice(
        nextState ? "Automated email checks enabled." : "Automated email checks paused."
      );
    } catch (err: unknown) {
      setActionError(sanitizeErrorMessage(err));
    } finally {
      setSavingSchedule(false);
    }
  };

  const handleIntervalChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newInterval = Number(e.target.value) as IngressIntervalMinutes;
    if (!config || savingSchedule) return;
    setSavingSchedule(true);
    setActionError(null);
    try {
      await updateConfig({ intervalMinutes: newInterval });
      showActionNotice("Check schedule updated.");
    } catch (err: unknown) {
      setActionError(sanitizeErrorMessage(err));
    } finally {
      setSavingSchedule(false);
    }
  };

  const handleTriggerNow = async () => {
    if (syncing || loading || syncingRef.current) return;
    syncingRef.current = true;
    setActionError(null);
    try {
      await triggerSync();
      showActionNotice("Email check completed.");
    } catch (err: unknown) {
      setActionError(sanitizeErrorMessage(err));
    } finally {
      syncingRef.current = false;
    }
  };

  const handleRefresh = async () => {
    clearNoticeTimer();
    setActionNotice(null);
    setActionError(null);
    setNoticeDismissed(false);
    await refresh();
  };

  const displayedNotice = !noticeDismissed ? actionNotice || notice : null;

  return (
    <div className="app-container" style={{ maxWidth: "960px" }}>
      <header className="page-header">
        <div>
          <h1 className="page-title">Settings</h1>
          <p className="page-subtitle">
            Manage your household transaction imports and configuration
          </p>
        </div>
        <div>
          <button
            type="button"
            onClick={handleRefresh}
            disabled={loading || syncing}
            className="btn btn-secondary btn-sm"
            aria-label="Refresh settings status"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>
      </header>

      {/* Action alerts and notices with auto-dismiss and manual dismiss */}
      {displayedNotice && (
        <div
          role="status"
          aria-live="polite"
          className="notice-box"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "var(--space-md)",
          }}
        >
          <span>{displayedNotice}</span>
          <button
            type="button"
            onClick={() => {
              clearNoticeTimer();
              setActionNotice(null);
              setNoticeDismissed(true);
            }}
            className="btn btn-secondary btn-sm"
            style={{
              minHeight: "26px",
              padding: "2px 8px",
              fontSize: "12px",
              lineHeight: 1,
            }}
            aria-label="Dismiss notice"
          >
            ✕
          </button>
        </div>
      )}

      {(error || actionError) && (
        <div role="alert" className="alert-box">
          {actionError || sanitizeErrorMessage(error)}
        </div>
      )}

      {/* SECTION: Email transactions */}
      <section className="settings-section" aria-labelledby="section-email-transactions">
        <div className="settings-section-header">
          <h2 id="section-email-transactions" className="settings-section-title">
            Email transactions
          </h2>
          <p className="settings-section-subtitle">
            Automatically add transactions from your email.
          </p>
          <p className="settings-context-note">
            Currently reads Axis Bank emails.
          </p>
        </div>

        {/* 2x2 Grid of primary cards */}
        <div className="settings-grid">
          {/* Card 1: Connection */}
          <div className="card settings-card" aria-labelledby="card-connection-heading">
            <div className="settings-card-header">
              <h3 id="card-connection-heading" className="card-title">
                Connection
              </h3>
              <span className={`badge ${connectionInfo.badgeClass}`} aria-label={`Status: ${connectionInfo.label}`}>
                {connectionInfo.label}
              </span>
            </div>
            <div className="settings-card-body">
              <p style={{ margin: 0, fontSize: "var(--font-body-sm-size)", color: "var(--ink-muted)" }}>
                {connectionInfo.message}
              </p>
            </div>
            <div className="settings-card-footer">
              <button
                type="button"
                disabled
                className="btn btn-secondary btn-sm"
                aria-disabled="true"
                title="Connect Gmail coming soon"
              >
                Connect Gmail (Coming soon)
              </button>
            </div>
          </div>

          {/* Card 2: Schedule */}
          <div className="card settings-card" aria-labelledby="card-schedule-heading">
            <div className="settings-card-header">
              <h3 id="card-schedule-heading" className="card-title">
                Schedule
              </h3>
              <button
                type="button"
                role="switch"
                aria-checked={isEnabled}
                aria-label="Toggle automated email checks"
                disabled={savingSchedule || loading}
                onClick={handleToggleEnabled}
                className="switch-control"
              >
                <span className="switch-track">
                  <span className="switch-thumb" />
                </span>
                <span style={{ fontSize: "var(--font-caption-size)", color: "var(--ink-muted)" }}>
                  {isEnabled ? "Enabled" : "Paused"}
                </span>
              </button>
            </div>
            <div className="settings-card-body">
              <div className="form-group" style={{ marginBottom: "var(--space-sm)" }}>
                <label htmlFor="check-interval-select" className="form-label">
                  Check my email every
                </label>
                <select
                  id="check-interval-select"
                  className="form-select"
                  value={intervalMinutes}
                  onChange={handleIntervalChange}
                  disabled={savingSchedule || loading}
                >
                  {INGRESS_INTERVAL_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ fontSize: "var(--font-caption-size)", color: "var(--ink-muted)" }}>
                Next check:{" "}
                <span
                  style={{ color: "var(--ink)", fontWeight: 500 }}
                  title={config?.nextRunAt || undefined}
                >
                  {formatFriendlyNextRun(config?.nextRunAt, isEnabled)}
                </span>
              </div>
            </div>
            <div className="settings-card-footer">
              <button
                type="button"
                onClick={handleTriggerNow}
                disabled={syncing || loading}
                className="btn btn-primary btn-sm"
                aria-label="Trigger email check now"
              >
                {syncing ? "Checking now..." : "Check now"}
              </button>
            </div>
          </div>

          {/* Card 3: Last Check */}
          <div className="card settings-card" aria-labelledby="card-last-check-heading">
            <div className="settings-card-header">
              <h3 id="card-last-check-heading" className="card-title">
                Last Check
              </h3>
              <span className={`badge ${executionBadge.badgeClass}`} aria-label={`Check state: ${executionBadge.label}`}>
                {executionBadge.label}
              </span>
            </div>
            <div className="settings-card-body">
              <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-xs)" }}>
                <div style={{ fontSize: "var(--font-caption-size)", color: "var(--ink-muted)" }}>
                  Last run time
                </div>
                <div
                  style={{ fontSize: "var(--font-heading-sm-size)", color: "var(--ink)" }}
                  title={status?.lastRunAt || undefined}
                >
                  {formatFriendlyDateTime(status?.lastRunAt)}
                </div>
              </div>

              <div style={{ marginTop: "var(--space-sm)" }}>
                <div style={{ fontSize: "var(--font-caption-size)", color: "var(--ink-muted)" }}>
                  Total transactions added so far
                </div>
                <div className="card-value" style={{ fontSize: "var(--font-display-md-size)" }}>
                  {status?.totalProcessed ?? 0}
                </div>
              </div>

              {status?.lastError && (
                <div
                  role="alert"
                  style={{
                    marginTop: "var(--space-sm)",
                    padding: "var(--space-xs) var(--space-sm)",
                    backgroundColor: "rgba(239, 68, 68, 0.15)",
                    border: "1px solid #ef4444",
                    borderRadius: "var(--radius-sm)",
                    color: "#fca5a5",
                    fontSize: "var(--font-caption-size)",
                  }}
                >
                  {sanitizeErrorMessage(status.lastError)}
                </div>
              )}
            </div>
          </div>

          {/* Card 4: What We Found */}
          <div className="card settings-card" aria-labelledby="card-found-heading">
            <div className="settings-card-header">
              <h3 id="card-found-heading" className="card-title">
                What We Found
              </h3>
            </div>
            <div className="settings-card-body">
              <p style={{ margin: 0, fontSize: "var(--font-body-sm-size)", color: "var(--ink-muted)" }}>
                Emails checked: <strong style={{ color: "var(--ink)" }}>{status?.totalProcessed ?? 0}</strong>
              </p>
              <p style={{ margin: 0, fontSize: "var(--font-caption-size)", color: "var(--ink-muted)" }}>
                Transactions needing categorization or manual confirmation are held for review.
              </p>
            </div>
            <div className="settings-card-footer">
              <Link href="/quarantine" className="btn btn-secondary btn-sm">
                Open Quarantine Review →
              </Link>
            </div>
          </div>
        </div>

        {/* Card 5: Logs */}
        <div className="card" aria-labelledby="card-logs-heading">
          <div className="card-title" id="card-logs-heading">
            Activity Logs
          </div>
          <div className="settings-placeholder-box">
            <p style={{ margin: 0, fontSize: "var(--font-body-sm-size)", color: "var(--ink)" }}>
              Check history will appear here
            </p>
            <p style={{ margin: "var(--space-xs) 0 0 0", fontSize: "var(--font-caption-size)", color: "var(--ink-muted)" }}>
              Check history will be added soon.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
