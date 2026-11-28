import test from "node:test";
import assert from "node:assert/strict";
import {
  clearTokenCache,
  getJwtExpMs,
  resolveAccessToken,
} from "./token-resolver.ts";

function createJwt(payload: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "RS256", typ: "JWT" })).toString("base64url");
  const body = Buffer.from(JSON.stringify(payload)).toString("base64url");
  return `${header}.${body}.signature`;
}

test("getJwtExpMs: parses exp correctly from JWT", () => {
  const expSec = Math.floor(Date.now() / 1000) + 3600;
  const jwt = createJwt({ exp: expSec, sub: "user-123" });
  assert.equal(getJwtExpMs(jwt), expSec * 1000);
});

test("getJwtExpMs: returns 0 on invalid token", () => {
  assert.equal(getJwtExpMs("not-a-jwt"), 0);
  assert.equal(getJwtExpMs("a.b"), 0);
});

test("token-resolver: returns null when window is undefined", async () => {
  clearTokenCache();
  const token = await resolveAccessToken();
  assert.equal(token, null);
});

test("token-resolver: fetches fresh token when window is defined", async () => {
  clearTokenCache();
  (globalThis as unknown as { window?: unknown }).window = {};

  const expSec = Math.floor(Date.now() / 1000) + 3600;
  const dummyJwt = createJwt({ exp: expSec, sub: "user-123" });

  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  globalThis.fetch = async (input: RequestInfo | URL) => {
    assert.equal(input.toString(), "/api/auth/token");
    fetchCount++;
    return new Response(JSON.stringify({ accessToken: dummyJwt }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const token = await resolveAccessToken();
    assert.equal(token, dummyJwt);
    assert.equal(fetchCount, 1);
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
    clearTokenCache();
  }
});

test("token-resolver: reuses in-memory cached token without refetching", async () => {
  clearTokenCache();
  (globalThis as unknown as { window?: unknown }).window = {};

  const expSec = Math.floor(Date.now() / 1000) + 3600;
  const dummyJwt = createJwt({ exp: expSec, sub: "user-123" });

  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  globalThis.fetch = async () => {
    fetchCount++;
    return new Response(JSON.stringify({ accessToken: dummyJwt }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const t1 = await resolveAccessToken();
    const t2 = await resolveAccessToken();
    assert.equal(t1, dummyJwt);
    assert.equal(t2, dummyJwt);
    assert.equal(fetchCount, 1); // Only 1 fetch call, second was cached in-memory!
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
    clearTokenCache();
  }
});

test("token-resolver: clearTokenCache forces fresh fetch", async () => {
  clearTokenCache();
  (globalThis as unknown as { window?: unknown }).window = {};

  const expSec = Math.floor(Date.now() / 1000) + 3600;
  const dummyJwt = createJwt({ exp: expSec, sub: "user-123" });

  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  globalThis.fetch = async () => {
    fetchCount++;
    return new Response(JSON.stringify({ accessToken: dummyJwt }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    await resolveAccessToken();
    assert.equal(fetchCount, 1);
    clearTokenCache();
    await resolveAccessToken();
    assert.equal(fetchCount, 2); // Refetched after cache cleared!
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
    clearTokenCache();
  }
});

test("token-resolver: refreshes when token expires within 45 seconds", async () => {
  clearTokenCache();
  (globalThis as unknown as { window?: unknown }).window = {};

  // Token expires in 30 seconds (within the 45-second early refresh window)
  const expiringSoonSec = Math.floor(Date.now() / 1000) + 30;
  const dummyJwt1 = createJwt({ exp: expiringSoonSec, sub: "user-1" });
  const freshSec = Math.floor(Date.now() / 1000) + 3600;
  const dummyJwt2 = createJwt({ exp: freshSec, sub: "user-2" });

  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  globalThis.fetch = async () => {
    fetchCount++;
    const token = fetchCount === 1 ? dummyJwt1 : dummyJwt2;
    return new Response(JSON.stringify({ accessToken: token }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const t1 = await resolveAccessToken();
    assert.equal(t1, dummyJwt1);
    assert.equal(fetchCount, 1);

    // Immediate second call should notice t1 is expiring within 45s and refetch
    const t2 = await resolveAccessToken();
    assert.equal(t2, dummyJwt2);
    assert.equal(fetchCount, 2);
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
    clearTokenCache();
  }
});

test("token-resolver: deduplicates concurrent in-flight requests", async () => {
  clearTokenCache();
  (globalThis as unknown as { window?: unknown }).window = {};

  const expSec = Math.floor(Date.now() / 1000) + 3600;
  const dummyJwt = createJwt({ exp: expSec, sub: "user-123" });

  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  globalThis.fetch = async () => {
    fetchCount++;
    await new Promise((resolve) => setTimeout(resolve, 10));
    return new Response(JSON.stringify({ accessToken: dummyJwt }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const [t1, t2, t3] = await Promise.all([
      resolveAccessToken(),
      resolveAccessToken(),
      resolveAccessToken(),
    ]);

    assert.equal(t1, dummyJwt);
    assert.equal(t2, dummyJwt);
    assert.equal(t3, dummyJwt);
    assert.equal(fetchCount, 1);
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
    clearTokenCache();
  }
});

test("token-resolver: returns null on 401 or non-ok response", async () => {
  clearTokenCache();
  (globalThis as unknown as { window?: unknown }).window = {};

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const token = await resolveAccessToken();
    assert.equal(token, null);
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
    clearTokenCache();
  }
});

test("token-resolver: returns null on network failure", async () => {
  clearTokenCache();
  (globalThis as unknown as { window?: unknown }).window = {};

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    throw new Error("Network offline");
  };

  try {
    const token = await resolveAccessToken();
    assert.equal(token, null);
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
    clearTokenCache();
  }
});
