let inFlightTokenPromise: Promise<string | null> | null = null;
let cachedAccessToken: string | null = null;
let cachedTokenExpiresAtMs: number = 0;

/**
 * Parses the expiration time (exp claim) from a JWT string.
 * Returns timestamp in epoch milliseconds, or 0 if unparseable.
 */
export function getJwtExpMs(token: string): number {
  try {
    const parts = token.split(".");
    if (parts.length < 2) return 0;
    // Decode base64url payload
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const jsonStr =
      typeof atob === "function"
        ? atob(base64)
        : Buffer.from(base64, "base64").toString("utf-8");
    const payload = JSON.parse(jsonStr);
    if (typeof payload.exp === "number") {
      return payload.exp * 1000;
    }
  } catch {
    // Ignore decode error
  }
  return 0;
}

/**
 * Clears the in-memory cached access token.
 * Call on 401 response or on user logout.
 */
export function clearTokenCache(): void {
  cachedAccessToken = null;
  cachedTokenExpiresAtMs = 0;
}

/**
 * Resolves an access token from memory cache or server session endpoint.
 * In-memory module cache avoids roundtrips to /api/auth/token on every request.
 * Refreshes 45s before JWT expiration.
 * Deduplicates in-flight concurrent requests.
 * Zero tokens in localStorage/sessionStorage.
 */
export async function resolveAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  const nowMs = Date.now();
  // If cached and still valid (refresh 45 seconds early)
  if (cachedAccessToken && cachedTokenExpiresAtMs - 45_000 > nowMs) {
    return cachedAccessToken;
  }

  if (inFlightTokenPromise) {
    return inFlightTokenPromise;
  }

  inFlightTokenPromise = (async () => {
    try {
      const res = await fetch("/api/auth/token");
      if (res.ok) {
        const data = await res.json();
        if (data && typeof data.accessToken === "string") {
          const token = data.accessToken;
          const expMs = getJwtExpMs(token);
          cachedAccessToken = token;
          // If exp is present use it, otherwise fallback to 1 minute safe TTL
          cachedTokenExpiresAtMs = expMs > nowMs ? expMs : nowMs + 60_000;
          return token;
        }
      }
    } catch {
      // Network or parsing error; return null to allow dev fallbacks
    }
    clearTokenCache();
    return null;
  })();

  try {
    return await inFlightTokenPromise;
  } finally {
    inFlightTokenPromise = null;
  }
}
