/**
 * The one place that talks HTTP.
 *
 * - The access token lives **in memory** and is injected per request; nothing
 *   is written to browser storage on purpose (Sprint 1 has no refresh tokens, so a
 *   reload must land on /login).
 * - A 401 is surfaced once: the session is cleared and the router sends the
 *   user to /login. No retry against a dead token.
 */

export type ApiErrorCode =
  | 'network'
  | 'unauthorized'
  | 'forbidden'
  | 'not_found'
  | 'conflict'
  | 'validation'
  | 'server'
  | 'unknown';

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;

  constructor(status: number, code: ApiErrorCode, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface ApiClientOptions {
  baseUrl?: string;
  getToken?: () => string | null;
  onUnauthorized?: () => void;
  fetchImpl?: typeof fetch;
}

function resolveBaseUrl(): string {
  const explicit = import.meta.env?.VITE_API_URL;
  const composeDefault = import.meta.env?.VITE_API_BASE_URL;
  return explicit || composeDefault || '/api';
}

function codeForStatus(status: number): ApiErrorCode {
  switch (status) {
    case 400:
    case 422:
      return 'validation';
    case 401:
      return 'unauthorized';
    case 403:
      return 'forbidden';
    case 404:
      return 'not_found';
    case 409:
      return 'conflict';
    default:
      return status >= 500 ? 'server' : 'unknown';
  }
}

function detailOf(body: unknown, fallback: string): string {
  if (typeof body === 'string' && body.trim()) return body;
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      const first = detail[0] as { msg?: string } | undefined;
      if (first?.msg) return first.msg;
    }
  }
  return fallback;
}

export class ApiClient {
  private readonly baseUrl: string;
  private readonly getToken: () => string | null;
  private readonly onUnauthorized?: () => void;
  private readonly fetchImpl: typeof fetch;

  constructor(options: ApiClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? resolveBaseUrl()).replace(/\/$/, '');
    this.getToken = options.getToken ?? (() => null);
    this.onUnauthorized = options.onUnauthorized;
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch.bind(globalThis);
  }

  private async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set('Accept', 'application/json');
    if (init.body !== undefined) headers.set('Content-Type', 'application/json');

    const token = this.getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    let response: Response;
    try {
      response = await this.fetchImpl(`${this.baseUrl}${path}`, {
        ...init,
        headers,
      });
    } catch {
      throw new ApiError(0, 'network', 'network request failed');
    }

    if (response.status === 401) {
      this.onUnauthorized?.();
      throw new ApiError(401, 'unauthorized', 'session expired');
    }

    if (!response.ok) {
      let body: unknown = null;
      try {
        body = await response.json();
      } catch {
        body = null;
      }
      throw new ApiError(
        response.status,
        codeForStatus(response.status),
        detailOf(body, `request failed with ${response.status}`),
      );
    }

    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  health(): Promise<{ status: string }> {
    return this.request('/health');
  }

  register(input: {
    email: string;
    password: string;
    display_name: string;
  }): Promise<AuthResponse> {
    return this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  login(input: { email: string; password: string }): Promise<AuthResponse> {
    return this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  }

  me(): Promise<AuthUser> {
    return this.request('/auth/me');
  }
}

export const api = new ApiClient();
