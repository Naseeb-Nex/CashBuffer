import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import { HeaderNav } from "@/shared/infrastructure/components/HeaderNav";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CashBuffer - Household Financial Management",
  description: "Clean Architecture Household Cash Flow & Expense Tracker with AI Assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={plusJakartaSans.variable}>
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
