import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "CashBuffer - Household Cash-Flow Tracking & AI Assistant",
  description:
    "Pure-precision household cash-flow intelligence. Automated Gmail receipt ingestion, smart categorization with quarantine review, and an autonomous AI financial assistant.",
};

export default function LandingPage() {
  return (
    <div className="landing-page">
      {/* Hero Section */}
      <section className="landing-hero" aria-labelledby="hero-title">
        <div className="landing-eyebrow">Household Intelligence</div>
        <h1 id="hero-title" className="landing-hero-title">
          Cycle-accurate cash flow for your household.
        </h1>
        <p className="landing-hero-subtitle">
          Real-time tracking of family cash flow, automated receipt ingestion, and an autonomous AI financial assistant keeping your liquid buffer intact.
        </p>
        <div className="landing-hero-actions">
          <Link href="/api/auth/login" className="btn btn-primary">
            Login
          </Link>
        </div>
      </section>

      {/* Feature Cards Section */}
      <section className="landing-features" aria-labelledby="features-title">
        <div className="landing-features-header">
          <div className="landing-eyebrow">Core Architecture</div>
          <h2 id="features-title" className="landing-section-title">
            Engineered for clarity and zero data loss.
          </h2>
        </div>

        <div className="landing-cards-grid">
          {/* Card 1: Automatic Gmail Ingestion */}
          <article className="card landing-feature-card">
            <div>
              <div className="landing-card-badge">01 · Ingestion</div>
              <h3 className="landing-card-title">Automatic Gmail Ingestion</h3>
              <p className="landing-card-copy">
                Streamline transaction capture with read-only inbox triggers. Digital receipts, subscription renewals, and bank alerts parse into structured records instantaneously without manual entry.
              </p>
            </div>
            <div className="landing-card-meta">
              <span>Read-only OAuth</span>
              <span className="dot-sep" aria-hidden="true">·</span>
              <span>Near-realtime</span>
            </div>
          </article>

          {/* Card 2: Smart Categorization & Quarantine Review */}
          <article className="card landing-feature-card">
            <div>
              <div className="landing-card-badge">02 · Quarantine</div>
              <h3 className="landing-card-title">Smart Categorization & Quarantine Review</h3>
              <p className="landing-card-copy">
                High-confidence expenses match deterministic rules automatically. Ambiguous vendor strings route to a dedicated quarantine queue for rapid, one-tap household review.
              </p>
            </div>
            <div className="landing-card-meta">
              <span>Deterministic rules</span>
              <span className="dot-sep" aria-hidden="true">·</span>
              <span>Zero data loss</span>
            </div>
          </article>

          {/* Card 3: AI Financial Assistant */}
          <article className="card landing-feature-card">
            <div>
              <div className="landing-card-badge">03 · Assistant</div>
              <h3 className="landing-card-title">AI Financial Assistant</h3>
              <p className="landing-card-copy">
                Conversational intelligence powered by strict household context. Query burn rates, upcoming cash obligations, and budget runway in plain language without exporting spreadsheets.
              </p>
            </div>
            <div className="landing-card-meta">
              <span>Multi-tenant safe</span>
              <span className="dot-sep" aria-hidden="true">·</span>
              <span>Natural language</span>
            </div>
          </article>
        </div>
      </section>

      {/* Short Footer */}
      <footer className="landing-footer" role="contentinfo">
        <div className="landing-footer-brand">
          <span className="footer-brand-name">CashBuffer</span>
          <span className="footer-tagline">Household cash-flow tracking and AI assistant</span>
        </div>
        <div className="landing-footer-copy">
          <span>&copy; 2026 CashBuffer. All rights reserved.</span>
        </div>
      </footer>
    </div>
  );
}
