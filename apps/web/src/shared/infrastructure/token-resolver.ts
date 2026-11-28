let inFlightTokenPromise: Promise<string | null> | null = null;

/**
 * Resolves a fresh access token from the server-side session endpoint.
 * No long-lived localStorage copies are retained.
 * Deduplicates in-flight concurrent requests.
 */
export async function resolveAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
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
          return data.accessToken;
        }
      }
    } catch {
      // Network or parsing error; return null to allow dev fallbacks
    }
    return null;
  })();

  try {
    return await inFlightTokenPromise;
  } finally {
    inFlightTokenPromise = null;
  }
}
