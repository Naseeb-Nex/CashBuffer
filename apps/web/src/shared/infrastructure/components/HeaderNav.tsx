"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useKindeBrowserClient, LoginLink, LogoutLink } from "@kinde-oss/kinde-auth-nextjs";

export function HeaderNav() {
  const pathname = usePathname();
  const { isAuthenticated, user } = useKindeBrowserClient();

  const isPublicLanding = pathname === "/";

  const links = [
    { href: "/dashboard", label: "Dashboard" },
    { href: "/quarantine", label: "Quarantine Review" },
    { href: "/settings", label: "Settings" },
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
        {isAuthenticated ? (
          <div className="nav-auth-container">
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
            <div className="nav-user-profile">
              <span className="user-email-badge" title={user?.email || "Authenticated"}>
                {user?.email || user?.given_name || "Account"}
              </span>
              <LogoutLink className="btn btn-secondary btn-sm">
                Logout
              </LogoutLink>
            </div>
          </div>
        ) : isPublicLanding ? (
          <LoginLink className="btn btn-primary btn-sm">
            Login
          </LoginLink>
        ) : (
          <div className="nav-auth-container">
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
            <LoginLink className="btn btn-primary btn-sm">
              Login
            </LoginLink>
          </div>
        )}
      </nav>
    </header>
  );
}
