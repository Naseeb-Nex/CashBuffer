import { ApiError } from "../domain/errors";

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
      this.baseUrl = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
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

    const defaultHeaders: Record<string, string> = {
      "Accept": "application/json",
      ...(token ? { "Authorization": `Bearer ${token}` } : {}),
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
        try {
          errorData = await response.json();
        } catch {
          errorData = await response.text();
        }
        const message = (errorData && typeof errorData === "object" && "detail" in errorData)
          ? String((errorData as { detail: unknown }).detail)
          : response.statusText || `HTTP request failed with status ${response.status}`;
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
