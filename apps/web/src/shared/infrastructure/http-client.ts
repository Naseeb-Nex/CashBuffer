import { ApiError } from "../domain/errors.ts";
import { clearTokenCache, resolveAccessToken } from "./token-resolver.ts";

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined | null>;
  token?: string;
}

export class HttpClient {
  private readonly baseUrl: string;

  constructor(baseUrl?: string) {
    // In browser, default to proxy /api/backend or provided base
    if (baseUrl) {
      this.baseUrl = baseUrl.replace(/\/$/, "");
    } else if (typeof window !== "undefined") {
      this.baseUrl = "/api/backend";
    } else {
      const base = (process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
      this.baseUrl = base.endsWith("/api/v1") ? base : `${base}/api/v1`;
    }
  }

  async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { params, token, headers = {}, ...rest } = options;
    const cleanPath = path.startsWith("/") ? path : `/${path}`;

    let url = `${this.baseUrl}${cleanPath}`;
    if (params) {
      const searchParams = new URLSearchParams();
      for (const [key, val] of Object.entries(params)) {
        if (val !== undefined && val !== null) {
          searchParams.append(key, String(val));
        }
      }
      const qs = searchParams.toString();
      if (qs) {
        url += (url.includes("?") ? "&" : "?") + qs;
      }
    }

    let activeToken = token;
    if (activeToken === undefined) {
      if (typeof window !== "undefined") {
        activeToken = (await resolveAccessToken()) || process.env.NEXT_PUBLIC_DEV_AUTH_TOKEN || "dev-user";
      } else {
        activeToken = process.env.NEXT_PUBLIC_DEV_AUTH_TOKEN || "dev-user";
      }
    }

    const defaultHeaders: Record<string, string> = {
      "Accept": "application/json",
      ...(activeToken ? { "Authorization": `Bearer ${activeToken}` } : {}),
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
    };

    const finalHeaders = {
      ...defaultHeaders,
      ...(headers as Record<string, string>),
    };

    try {
      const response = await fetch(url, {
        ...rest,
        headers: finalHeaders,
      });

      if (!response.ok) {
        let errorData: unknown;
        const text = await response.text();
        try {
          errorData = text ? JSON.parse(text) : undefined;
        } catch {
          errorData = text || undefined;
        }

        let message: string | undefined;
        if (errorData && typeof errorData === "object") {
          if ("detail" in errorData && (errorData as { detail: unknown }).detail != null) {
            const detail = (errorData as { detail: unknown }).detail;
            message = typeof detail === "string" ? detail : JSON.stringify(detail);
          } else if ("message" in errorData && (errorData as { message: unknown }).message != null) {
            const msg = (errorData as { message: unknown }).message;
            message = typeof msg === "string" ? msg : JSON.stringify(msg);
          }
        } else if (typeof errorData === "string" && errorData.trim()) {
          const trimmed = errorData.trim();
          if (!trimmed.startsWith("<")) {
            message = trimmed;
          }
        }

        if (!message) {
          message = response.statusText || `HTTP request failed with status ${response.status}`;
        }

        if (response.status === 401) {
          clearTokenCache();
        }

        throw new ApiError(message, response.status, errorData);
      }

      if (response.status === 204) {
        return undefined as T;
      }

      return (await response.json()) as T;
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        throw err;
      }
      throw new ApiError(
        err instanceof Error ? err.message : "Network error occurred",
        0,
        err
      );
    }
  }

  get<T>(path: string, options?: Omit<RequestOptions, "method" | "body">): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  post<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "POST",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body?: unknown, options?: Omit<RequestOptions, "method" | "body">): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "PATCH",
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(path: string, options?: Omit<RequestOptions, "method">): Promise<T> {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }
}

export const defaultHttpClient = new HttpClient();
