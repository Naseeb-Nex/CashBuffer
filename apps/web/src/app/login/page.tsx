import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Login - CashBuffer",
  description: "Sign in to CashBuffer household cash-flow tracking",
};

export default function LoginPage() {
  return (
    <div className="login-container">
      <div className="card login-card">
        <div className="landing-card-badge" style={{ marginBottom: "var(--space-sm)" }}>
          CashBuffer Auth
        </div>
        <h1 className="login-title">Sign In to CashBuffer</h1>
        <p className="login-subtitle">
          Household cash-flow intelligence and autonomous AI assistant. Sign in with your account or register a new household.
        </p>
        <div className="login-actions">
          <Link href="/api/auth/login" className="btn btn-primary">
            Sign In
          </Link>
          <Link href="/api/auth/register" className="btn btn-secondary">
            Register
          </Link>
        </div>
        <div style={{ marginTop: "var(--space-lg)", borderTop: "1px solid var(--border-subtle)", paddingTop: "var(--space-md)" }}>
          <Link href="/" className="nav-item" style={{ fontSize: "var(--font-caption-size)" }}>
            ← Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
