import test from "node:test";
import assert from "node:assert/strict";
import { resolveAccessToken } from "./token-resolver.ts";

test("token-resolver: returns null when window is undefined", async () => {
  const token = await resolveAccessToken();
  assert.equal(token, null);
});

test("token-resolver: fetches fresh token when window is defined", async () => {
  (globalThis as unknown as { window?: unknown }).window = {};

  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  globalThis.fetch = async (input: RequestInfo | URL) => {
    assert.equal(input.toString(), "/api/auth/token");
    fetchCount++;
    return new Response(JSON.stringify({ accessToken: "fresh-access-token-123" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const token = await resolveAccessToken();
    assert.equal(token, "fresh-access-token-123");
    assert.equal(fetchCount, 1);
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
  }
});

test("token-resolver: deduplicates concurrent in-flight requests", async () => {
  (globalThis as unknown as { window?: unknown }).window = {};

  const originalFetch = globalThis.fetch;
  let fetchCount = 0;
  globalThis.fetch = async () => {
    fetchCount++;
    // Add micro-delay to simulate network
    await new Promise((resolve) => setTimeout(resolve, 10));
    return new Response(JSON.stringify({ accessToken: "concurrent-token" }), {
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

    assert.equal(t1, "concurrent-token");
    assert.equal(t2, "concurrent-token");
    assert.equal(t3, "concurrent-token");
    assert.equal(fetchCount, 1);
  } finally {
    globalThis.fetch = originalFetch;
    delete (globalThis as unknown as { window?: unknown }).window;
  }
});

test("token-resolver: returns null on 401 or non-ok response", async () => {
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
  }
});

test("token-resolver: returns null on network failure", async () => {
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
  }
});
