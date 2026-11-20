---
name: evervault-cashbuffer
description: Evervault visual design system tokens and components customized for CashBuffer financial application.
colors:
  primary: "#ffffff"
  secondary: "#94a3b8"
  muted: "#64748b"
  neutral: "#010314"
  surface: "#0b0d1c"
  surface-hover: "#12162e"
  surface-card: "#0d1127"
  border: "rgba(255, 255, 255, 0.08)"
  border-glow: "rgba(158, 158, 255, 0.25)"
  border-focus: "#6633ee"
  accent-purple: "#6633ee"
  accent-indigo: "#4f46e5"
  accent-lavender: "#9e9eff"
  accent-cyan: "#06b6d4"
  accent-emerald: "#10b981"
  accent-amber: "#f59e0b"
  accent-rose: "#f43f5e"
  on-primary: "#ffffff"
  on-accent: "#ffffff"
  gradient-hero: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(102, 51, 238, 0.25), transparent 75%)"
  gradient-glow: "radial-gradient(circle at 50% 50%, rgba(158, 158, 255, 0.08), transparent 70%)"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "3.5rem"
    fontWeight: "700"
    letterSpacing: "-0.04em"
    lineHeight: "1.1"
  h1:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "2.75rem"
    fontWeight: "700"
    letterSpacing: "-0.035em"
    lineHeight: "1.15"
  h2:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "2rem"
    fontWeight: "600"
    letterSpacing: "-0.03em"
    lineHeight: "1.25"
  h3:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1.25rem"
    fontWeight: "600"
    letterSpacing: "-0.02em"
    lineHeight: "1.4"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "1rem"
    fontWeight: "400"
    lineHeight: "1.6"
  body-sm:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: "400"
    lineHeight: "1.5"
  label:
    fontFamily: "JetBrains Mono, SF Mono, Menlo, monospace"
    fontSize: "0.75rem"
    fontWeight: "500"
    letterSpacing: "0.06em"
    textTransform: "uppercase"
rounded:
  sm: "6px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "32px"
  xxl: "48px"
  hero: "80px"
components:
  button-primary:
    backgroundColor: "#ffffff"
    textColor: "#010314"
    hoverBackgroundColor: "#e2e8f0"
    rounded: "9999px"
    padding: "10px 22px"
    fontWeight: "600"
    fontSize: "0.9375rem"
  button-secondary:
    backgroundColor: "rgba(255, 255, 255, 0.06)"
    textColor: "#ffffff"
    borderColor: "rgba(255, 255, 255, 0.12)"
    hoverBackgroundColor: "rgba(255, 255, 255, 0.1)"
    hoverBorderColor: "#9e9eff"
    rounded: "9999px"
    padding: "10px 22px"
    fontWeight: "500"
    fontSize: "0.9375rem"
  button-glow:
    backgroundColor: "#6633ee"
    textColor: "#ffffff"
    hoverBackgroundColor: "#582be8"
    boxShadow: "0 0 20px rgba(102, 51, 238, 0.45)"
    rounded: "9999px"
    padding: "10px 22px"
    fontWeight: "600"
    fontSize: "0.9375rem"
  card:
    backgroundColor: "#0b0d1c"
    borderColor: "rgba(255, 255, 255, 0.08)"
    hoverBorderColor: "rgba(158, 158, 255, 0.25)"
    rounded: "16px"
    padding: "24px"
  badge:
    backgroundColor: "rgba(102, 51, 238, 0.12)"
    borderColor: "rgba(158, 158, 255, 0.3)"
    textColor: "#9e9eff"
    rounded: "9999px"
    padding: "4px 12px"
---

# Evervault Design System & CashBuffer Adaptation

## 1. Evervault Visual Design System (Source: https://evervault.com/)

Evervault is a developer-first data security and encryption platform. Its visual design system conveys cryptographic security, precision, and enterprise trust through an obsidian dark theme accented with luminous electric violet and lavender hues.

### 1.1 Color Palette
- **Canvas / Root Background**: Deep obsidian (`#010314`), almost true black with a very subtle deep blue undertone.
- **Surface Elevation**: Layered cosmic containers (`#0b0d1c`, `#0d1127`, `rgba(255, 255, 255, 0.03)`).
- **Primary Brand Accent**: Electric Violet (`#6633ee`) and Vivid Indigo (`#4f46e5`).
- **Secondary Accent & Text Highlight**: Periwinkle / Lavender (`#9e9eff`).
- **Borders & Dividers**: Hairline subtle borders (`rgba(255, 255, 255, 0.08)` to `rgba(255, 255, 255, 0.15)`), often illuminated with subtle violet/blue edge gradients on hover.
- **Typography Colors**:
  - Primary: Pure white (`#ffffff`) or high-opacity text (`rgba(255, 255, 255, 0.95)`).
  - Secondary: Slate-300 / 400 (`#94a3b8`, `rgba(255, 255, 255, 0.65)`).
  - Monospace / Metadata: Violet-tinted slate or lavender (`#9e9eff`).

### 1.2 Typography
- **Headings**: Geometric modern sans-serif (Roobert / Inter) with tight negative tracking (`-0.03em` to `-0.04em`), strong visual hierarchy, and crisp kerning.
- **Body**: Highly legible clean sans-serif with comfortable line height (1.6) and high contrast against dark surfaces.
- **Code & Security Tokens**: Monospaced font (`JetBrains Mono`, `SF Mono`) for cryptographic tokens, API requests, hashes, and payload schemas.

### 1.3 Components & Geometry
- **Buttons**:
  - Full-pill borders (`border-radius: 9999px`).
  - High-contrast white buttons with dark text for primary calls to action.
  - Ghost / glass buttons with translucent backgrounds and subtle white/violet borders.
  - Interactive hover transitions with soft scale and border illumination.
- **Cards & Surfaces**:
  - Soft rounded corners (`16px` to `24px`).
  - Dark glassmorphism (`backdrop-filter: blur(12px)` over deep indigo radial gradients).
  - Subtle grid backgrounds (`background-image: radial-gradient(rgba(255,255,255,0.1) 1px, transparent 1px)`).
- **Badges & Micro-UI**:
  - Pill badges with glowing borders and mono/label text.
  - Terminal-like code visualizers with syntax highlighting and interactive copy actions.

### 1.4 Tone & Experience
- **Developer-First & High Assurance**: Clean, mathematically precise, uncluttered, giving instant confidence in security and engineering rigor.
- **Atmospheric Lighting**: Deep dark void energized by focused violet and blue neon gradients.

---

## 2. CashBuffer Customization

CashBuffer adapts Evervault's security-first design system to personal cash-flow sovereignty, intelligent financial ingestion, and buffer preservation.

### 2.1 Adapted Semantic Tokens
- **Buffer Safety (Inflow / Green)**: `#10b981` (Emerald 500) — represents positive buffer liquidity, incoming income, and verified ledger balance.
- **Buffer Threshold (Warning / Amber)**: `#f59e0b` (Amber 500) — signals cash buffer approaching low limits.
- **Quarantine Sandbox (Risk / Rose)**: `#f43f5e` (Rose 500) — represents unverified or quarantined transactions pending review.
- **Clean Architecture Foundation**: Electric violet (`#6633ee`) and lavender (`#9e9eff`) indicate AI automation, automated ingestion daemons, and core domain invariants.

### 2.2 Landing Page Structure
1. **Global Navigation Bar**:
   - Brand logo with gradient badge ("Clean Architecture").
   - Quick navigation links (Features, Architecture, Ingress, AI Engine).
   - Prominent **Log In** button linking directly to `/login`.
   - Primary **Launch Dashboard** CTA linking to `/dashboard`.
2. **Hero Section**:
   - Eyebrow badge: `Autonomous Cash Buffer Engine v2.0`.
   - Display headline: "Take control of your household cash buffer".
   - Subtitle emphasizing clean architecture, automated ingestion, quarantine sandbox, and real-time AI assistant.
   - Dual CTAs: Primary "Launch Dashboard", Secondary "Sign In to CashBuffer" (`/login`).
   - Interactive Live Buffer Simulator previewing real-time cash balance, safe spend gauge, and recent ledger entries.
3. **Core Pillars / Feature Grid**:
   - **Autonomous Ingress**: Automated email/SMS ingestion daemon with idempotent deduplication.
   - **Quarantine Review Sandbox**: Isolate suspicious or unverified inflows before they hit the ledger.
   - **Real-Time Buffer Health**: Dynamic safe-to-spend computation preventing overdrafts and panic.
   - **AI Financial Co-Pilot**: LLM assistant with domain-grounded transaction tools and budget insights.
4. **Interactive Architecture & Invariant Showcase**:
   - Visual comparison of standard messy personal finance apps vs. CashBuffer's strict Clean Architecture domain isolation.
5. **Call To Action Banner**:
   - Full-width glowing gradient banner.
   - Direct access to `/dashboard` and clearly visible `/login` button.
6. **Footer**:
   - Repository links, architecture documentation, status badges, and copyright.
