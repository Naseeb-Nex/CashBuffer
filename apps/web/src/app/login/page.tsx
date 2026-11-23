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
        <h1 className="login-title">Login coming soon</h1>
        <p className="login-subtitle">
          Secure household authentication is currently in development. You will soon be able to authenticate and manage your household cash buffer.
        </p>
        <div className="login-actions">
          <Link href="/dashboard" className="btn btn-primary btn-sm">
            Go to Dashboard
          </Link>
          <Link href="/" className="btn btn-secondary btn-sm">
            Back to Home
          </Link>
        </div>
      </div>
    </div>
  );
}
