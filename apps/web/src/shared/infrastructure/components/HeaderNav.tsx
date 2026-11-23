"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export function HeaderNav() {
  const pathname = usePathname();

  const isPublicLanding = pathname === "/";

  const links = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/quarantine", label: "Quarantine Review" },
    { href: "/ingress", label: "Ingress & Cron" },
    { href: "/chat", label: "AI Financial Chat" },
  ];

  return (
    <header className="header-bar" role="banner">
      <div className="brand">
        <Link href="/">
          <span>CashBuffer</span>
        </Link>
      </div>
      <nav aria-label="Main Navigation">
        {isPublicLanding ? (
          <Link href="/login" className="btn btn-primary btn-sm">
            Login
          </Link>
        ) : (
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
        )}
      </nav>
    </header>
  );
}
