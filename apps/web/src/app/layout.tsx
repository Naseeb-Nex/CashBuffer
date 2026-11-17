import type { Metadata } from "next";
import { HeaderNav } from "@/shared/infrastructure/components/HeaderNav";
import "./globals.css";

export const metadata: Metadata = {
  title: "CashBuffer - Financial Management & Ingress",
  description: "Clean Architecture Household Cash Flow & Expense Tracker with AI Assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <a href="#main-content" className="skip-link">
          Skip to main content
        </a>
        <HeaderNav />
        <main id="main-content" className="app-container" tabIndex={-1}>
          {children}
        </main>
      </body>
    </html>
  );
}
