"use client";

import Link from "next/link";

export default function LoginPage() {
  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="brand" style={{ justifyContent: "center", marginBottom: "0.5rem" }}>
            <span>CashBuffer</span>
            <span className="brand-badge">Auth</span>
          </div>
          <h1 className="login-title">Sign in to CashBuffer</h1>
          <p className="login-subtitle">
            Household Cash Flow &amp; Expense Tracker with Ingress Engine
          </p>
        </div>

        {/* Notice explaining auth state */}
        <div className="auth-notice" role="note">
          <div className="auth-notice-title">Authentication Route Notice</div>
          <p className="auth-notice-body">
            No external auth/OAuth provider is currently active in this workspace. Direct access is enabled for local evaluation.
          </p>
        </div>

        <form className="login-form" onSubmit={(e) => e.preventDefault()}>
          <div className="form-group">
            <label htmlFor="login-email" className="form-label">Email Address</label>
            <input
              id="login-email"
              type="email"
              className="form-input"
              placeholder="name@household.finance"
              defaultValue="admin@cashbuffer.local"
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password" className="form-label">Password</label>
            <input
              id="login-password"
              type="password"
              className="form-input"
              placeholder="••••••••••••"
              defaultValue="password123"
            />
          </div>

          <Link href="/dashboard" className="btn btn-primary btn-full" style={{ textAlign: "center" }}>
            Sign In &amp; Launch Dashboard
          </Link>
        </form>

        <div className="login-footer">
          <Link href="/" className="login-back-link">
            &larr; Back to Landing Page
          </Link>
        </div>
      </div>
    </div>
  );
}
