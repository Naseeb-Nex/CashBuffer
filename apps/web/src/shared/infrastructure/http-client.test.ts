import test from "node:test";
import assert from "node:assert/strict";
import { HttpClient } from "./http-client.ts";

test("HttpClient: constructs correct base URL and prepends /api/v1 for SSR", () => {
  const client = new HttpClient("http://custom-api:8000");
  // @ts-expect-error accessing private baseUrl for assertion
  assert.equal(client.baseUrl, "http://custom-api:8000");
});

test("HttpClient: request sends default auth token and serializes query params", async () => {
  let capturedUrl = "";
  let capturedHeaders: Record<string, string> = {};

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    capturedUrl = input.toString();
    capturedHeaders = (init?.headers || {}) as Record<string, string>;
    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const client = new HttpClient("http://localhost:8000/api/v1");
    const result = await client.get<{ success: boolean }>("/transactions", {
      params: { limit: 10, search: "swiggy" },
    });

    assert.equal(result.success, true);
    assert.equal(capturedUrl, "http://localhost:8000/api/v1/transactions?limit=10&search=swiggy");
    assert.equal(capturedHeaders["Authorization"], "Bearer dev-user");
    assert.equal(capturedHeaders["Accept"], "application/json");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("HttpClient: throws ApiError on non-200 response with detail message", async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    return new Response(JSON.stringify({ detail: "Transaction not found" }), {
      status: 404,
      headers: { "Content-Type": "application/json" },
    });
  };

  try {
    const client = new HttpClient("http://localhost:8000/api/v1");
    await assert.rejects(
      async () => {
        await client.get("/transactions/999");
      },
      (err: any) => {
        assert.equal(err.name, "ApiError");
        assert.equal(err.statusCode, 404);
        assert.equal(err.message, "Transaction not found");
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});
