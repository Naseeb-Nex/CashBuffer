"use client";

import { useState } from "react";
import Link from "next/link";

export default function LandingPage() {
  // Interactive Buffer Simulator state
  const [balance, setBalance] = useState(142850);
  const [monthlyInflow, setMonthlyInflow] = useState(185000);
  const [monthlyOutflow, setMonthlyOutflow] = useState(98500);
  const [quarantinedCount, setQuarantinedCount] = useState(3);
  const [lastAction, setLastAction] = useState<string | null>(null);

  // Buffer runway calculation (days of safe runway based on net balance and daily outflow)
  const dailyBurn = monthlyOutflow / 30;
  const runwayDays = Math.max(0, Math.round(balance / (dailyBurn > 0 ? dailyBurn : 1)));

  const handleSimulateSalary = () => {
    setBalance((prev) => prev + 95000);
    setMonthlyInflow((prev) => prev + 95000);
    setLastAction("✓ Inflow recorded: +₹95,000 (TechCorp Salary) — Buffer increased.");
  };

  const handleSimulateRent = () => {
    setBalance((prev) => Math.max(0, prev - 28000));
    setMonthlyOutflow((prev) => prev + 28000);
    setLastAction("− Outflow processed: −₹28,000 (Monthly Rent) — Invariants verified.");
  };

  const handleSimulateQuarantine = () => {
    setQuarantinedCount((prev) => prev + 1);
    setLastAction("⚠ Unverified SMS parsed: flagged for quarantine review (Confidence < 0.85).");
  };

  const handleResetSimulator = () => {
    setBalance(142850);
    setMonthlyInflow(185000);
    setMonthlyOutflow(98500);
    setQuarantinedCount(3);
    setLastAction(null);
  };

  return (
    <div className="landing-wrapper">
      {/* 1. Hero Section */}
      <section className="hero-section" aria-labelledby="hero-title">
        <div className="hero-badge-wrapper">
          <div className="hero-pill-badge">
            <span>●</span> Autonomous Cash Buffer Engine v2.0 • Clean Architecture
          </div>
        </div>

        <h1 id="hero-title" className="hero-title">
          Take control of your <span className="hero-title-highlight">household cash buffer</span>
        </h1>

        <p className="hero-subtitle">
          Separate transaction ingestion and financial tracking from fragile single-point processors.
          Ingest bank SMS, statements, and feeds into an isolated quarantine sandbox with zero ledger drift.
        </p>

        <div className="hero-cta-group">
          <Link href="/dashboard" className="btn-pill-primary" aria-label="Launch CashBuffer Dashboard">
            Launch Dashboard &rarr;
          </Link>
          <Link href="/login" className="btn-pill-secondary" aria-label="Sign in to your CashBuffer account">
            Log In to Account
          </Link>
        </div>

        {/* Interactive Live Buffer Simulator */}
        <div className="simulator-card" aria-label="Interactive Cash Buffer Simulator">
          <div className="simulator-header">
            <div>
              <div className="simulator-title">Live Buffer Telemetry Simulator</div>
              <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                Calculated dynamically via Clean Architecture Domain Services
              </div>
            </div>
            <div className="simulator-status-pill resilient">
              ● Buffer Resilient (Runway &gt; 30d)
            </div>
          </div>

          <div className="simulator-metrics">
            <div className="sim-metric-box">
              <div className="sim-metric-label">Net Cash Buffer</div>
              <div className="sim-metric-val green">
                ₹{balance.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="sim-metric-box">
              <div className="sim-metric-label">Safe Runway</div>
              <div className="sim-metric-val purple">
                {runwayDays} Days
              </div>
            </div>

            <div className="sim-metric-box">
              <div className="sim-metric-label">Monthly Inflow</div>
              <div className="sim-metric-val green">
                ₹{monthlyInflow.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </div>
            </div>

            <div className="sim-metric-box">
              <div className="sim-metric-label">Quarantine Sandbox</div>
              <div className="sim-metric-val amber">
                {quarantinedCount} Pending
              </div>
            </div>
          </div>

          {lastAction && (
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.75rem",
                color: "var(--accent-lavender)",
                padding: "0.5rem 0.75rem",
                background: "rgba(102, 51, 238, 0.1)",
                borderRadius: "var(--radius-sm)",
                marginBottom: "1rem",
              }}
            >
              {lastAction}
            </div>
          )}

          <div className="sim-actions">
            <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)", alignSelf: "center", marginRight: "0.25rem" }}>
              Simulate Ingress Event:
            </span>
            <button type="button" onClick={handleSimulateSalary} className="sim-btn">
              + Add Salary (₹95,000)
            </button>
            <button type="button" onClick={handleSimulateRent} className="sim-btn">
              − Pay Rent (₹28,000)
            </button>
            <button type="button" onClick={handleSimulateQuarantine} className="sim-btn">
              ⚠ Ingest Suspicious SMS
            </button>
            <button type="button" onClick={handleResetSimulator} className="sim-btn" style={{ marginLeft: "auto", opacity: 0.7 }}>
              Reset
            </button>
          </div>
        </div>
      </section>

      {/* 2. Core Feature Pillars Grid */}
      <section className="features-section" aria-labelledby="features-title">
        <div style={{ textAlign: "center" }}>
          <div className="section-eyebrow">Enterprise-Grade Infrastructure</div>
          <h2 id="features-title" className="section-title">Engineered for Sovereign Household Finance</h2>
          <p className="section-desc" style={{ margin: "0 auto 2.5rem auto" }}>
            Built strictly on Clean Architecture principles, ensuring zero vendor lock-in, deterministic ledger accuracy, and complete data isolation.
          </p>
        </div>

        <div className="feature-grid-4">
          <div className="feature-card">
            <div className="feature-icon-wrapper">&#9881;</div>
            <h3 className="feature-heading">Autonomous Ingress Daemon</h3>
            <p className="feature-text">
              Background cron runners poll email and SMS feeds with exponential backoff and idempotent SHA-256 deduplication to prevent double-counting.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper">&#9762;</div>
            <h3 className="feature-heading">Quarantine Review Sandbox</h3>
            <p className="feature-text">
              Transactions with parse ambiguity or low OCR confidence are quarantined automatically. Protects your ledger from hallucinated records.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper">&#9879;</div>
            <h3 className="feature-heading">Dynamic Buffer Protection</h3>
            <p className="feature-text">
              Monitors safe-to-spend runways and burn rates across multi-tenant household entities, alerting before cash buffers dip below safety thresholds.
            </p>
          </div>

          <div className="feature-card">
            <div className="feature-icon-wrapper">&#9889;</div>
            <h3 className="feature-heading">AI Financial Intelligence</h3>
            <p className="feature-text">
              Context-aware LLM copilot connected via structured tools. Ask natural questions about spending anomalies, burn trajectory, and budget caps.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Comparison Matrix: Traditional vs Clean Architecture */}
      <section className="comparison-section" aria-labelledby="comparison-title">
        <div style={{ textAlign: "center" }}>
          <div className="section-eyebrow">Architectural Contrast</div>
          <h2 id="comparison-title" className="section-title">The Clean Architecture Difference</h2>
          <p className="section-desc" style={{ margin: "0 auto 2.5rem auto" }}>
            Evervault revolutionized payment collection by eliminating processor coupling. CashBuffer brings the same decoupling to personal finances.
          </p>
        </div>

        <div className="comparison-grid">
          <div className="comparison-card legacy">
            <div className="comparison-badge">Typical Financial SaaS</div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 600, color: "#ffffff", marginBottom: "1rem" }}>
              Fragile &amp; Coupled
            </h3>
            <ul className="comparison-list">
              <li className="comparison-item">
                <span style={{ color: "var(--accent-red)" }}>✕</span>
                <span>Third-party aggregators break connections and force manual re-linking.</span>
              </li>
              <li className="comparison-item">
                <span style={{ color: "var(--accent-red)" }}>✕</span>
                <span>Unverified bank transactions mutate your balances without review.</span>
              </li>
              <li className="comparison-item">
                <span style={{ color: "var(--accent-red)" }}>✕</span>
                <span>Financial data stored in centralized SaaS clouds and monetized for ad targeting.</span>
              </li>
              <li className="comparison-item">
                <span style={{ color: "var(--accent-red)" }}>✕</span>
                <span>Tightly coupled spaghetti code that breaks when bank API schemas drift.</span>
              </li>
            </ul>
          </div>

          <div className="comparison-card clean-arch">
            <div className="comparison-badge">CashBuffer Clean Architecture</div>
            <h3 style={{ fontSize: "1.2rem", fontWeight: 600, color: "#ffffff", marginBottom: "1rem" }}>
              Decoupled &amp; Invariant-Enforced
            </h3>
            <ul className="comparison-list">
              <li className="comparison-item">
                <span style={{ color: "var(--accent-green)" }}>✓</span>
                <span><strong>Provider-Agnostic Ingress:</strong> Ingest from local SMS, CSV, webhooks, or daemons.</span>
              </li>
              <li className="comparison-item">
                <span style={{ color: "var(--accent-green)" }}>✓</span>
                <span><strong>Quarantine Isolation:</strong> Ambiguous entries require explicit approval before ledger commit.</span>
              </li>
              <li className="comparison-item">
                <span style={{ color: "var(--accent-green)" }}>✓</span>
                <span><strong>Sovereign Privacy:</strong> Local SQLite or dedicated Postgres with strict tenant boundary isolation.</span>
              </li>
              <li className="comparison-item">
                <span style={{ color: "var(--accent-green)" }}>✓</span>
                <span><strong>Domain-Driven Resilience:</strong> Core domain invariants hold true regardless of UI or transport layer.</span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* 4. Code & Invariant Showcase */}
      <section className="code-showcase-section" aria-labelledby="code-title">
        <div style={{ textAlign: "center" }}>
          <div className="section-eyebrow">Developer &amp; Systems First</div>
          <h2 id="code-title" className="section-title">Deterministic Ingress &amp; Verification</h2>
          <p className="section-desc" style={{ margin: "0 auto 2.5rem auto" }}>
            Every raw transaction passes through immutable domain policies and quarantine evaluation before touching your ledger.
          </p>
        </div>

        <div className="code-window">
          <div className="code-window-header">
            <div className="code-dots">
              <div className="code-dot" />
              <div className="code-dot" />
              <div className="code-dot" />
            </div>
            <div className="code-filename">domain/services/ingress_pipeline.py</div>
            <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.75rem", color: "var(--accent-lavender)" }}>
              Python 3.12 • Clean Architecture
            </div>
          </div>
          <pre className="code-content">
{`# CashBuffer Domain Invariant: Zero Unchecked Mutations
class IngressPipeline:
    def process_raw_signal(self, payload: RawSignal) -> IngestionResult:
        fingerprint = calculate_idempotency_key(payload)
        if self.ledger.has_seen(fingerprint):
            return IngestionResult.duplicate(fingerprint)

        parsed_tx = self.parser.extract(payload.raw_text)
        if parsed_tx.confidence < THRESHOLD_QUARANTINE_MIN:
            # Route to Quarantine Sandbox for manual audit
            quarantine_id = self.quarantine_repo.isolate(parsed_tx)
            return IngestionResult.quarantined(quarantine_id)

        # Domain verification: Buffer invariants and ledger update
        return self.ledger.commit_inflow_or_outflow(parsed_tx)`}
          </pre>
        </div>
      </section>

      {/* 5. Call To Action Banner */}
      <section className="cta-banner" aria-labelledby="cta-title">
        <h2 id="cta-title" className="cta-banner-title">
          Ready to build your financial fortress?
        </h2>
        <p className="cta-banner-desc">
          Monitor your cash buffer, automate ingress pipelines, and isolate unverified transactions in minutes.
        </p>
        <div style={{ display: "flex", gap: "1rem", justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/dashboard" className="btn-pill-primary" aria-label="Enter CashBuffer Dashboard">
            Open Dashboard
          </Link>
          <Link href="/login" className="btn-pill-secondary" aria-label="Log in to existing CashBuffer session">
            Log In
          </Link>
        </div>
      </section>

      {/* 6. Footer */}
      <footer className="landing-footer" role="contentinfo">
        <div>
          <span style={{ fontWeight: 600, color: "#ffffff" }}>CashBuffer</span> — Sovereign Household Cash Flow &amp; Expense Ingress.
        </div>
        <div className="footer-links">
          <Link href="/dashboard" className="footer-link">Dashboard</Link>
          <Link href="/quarantine" className="footer-link">Quarantine</Link>
          <Link href="/ingress" className="footer-link">Ingress</Link>
          <Link href="/chat" className="footer-link">AI Chat</Link>
          <Link href="/login" className="footer-link">Log In</Link>
          <Link href="/docs/design.md" className="footer-link">Design Spec</Link>
        </div>
      </footer>
    </div>
  );
}
