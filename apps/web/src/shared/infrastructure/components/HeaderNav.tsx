"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function HeaderNav() {
  const pathname = usePathname();

  const links = [
    { href: "/", label: "Home" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/quarantine", label: "Quarantine Review" },
    { href: "/ingress", label: "Ingress & Cron" },
    { href: "/chat", label: "AI Financial Chat" },
  ];

  return (
    <header className="header-bar" role="banner">
      <Link href="/" className="brand" aria-label="CashBuffer Home">
        <span>CashBuffer</span>
        <span className="brand-badge">Clean Arch</span>
      </Link>
      <nav aria-label="Main Navigation">
        <ul className="nav-links">
          {links.map((link) => {
            const isActive = pathname === link.href;
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className={`nav-item ${isActive ? "active" : ""}`}
                  aria-current={isActive ? "page" : undefined}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="header-actions">
        <Link href="/login" className="login-btn" aria-label="Log in to CashBuffer">
          Log in
        </Link>
      </div>
    </header>
  );
}
