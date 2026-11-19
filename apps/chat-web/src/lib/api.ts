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

export interface PeerSummary {
  id: string;
  display_name: string;
}

export interface Conversation {
  id: string;
  type: string;
  created_at: string;
  last_message_at: string | null;
  last_message_preview: string | null;
  peer: PeerSummary;
}

export interface ChatMessage {
  id: string;
  conversation_id: string;
  sender_id: string;
  seq: number;
  body: string;
  client_msg_id: string | null;
  created_at: string;
}

export interface MessagePage {
  items: ChatMessage[];
  next_before_seq: number | null;
  has_more: boolean;
}

/** ws(s)://…/ws for the same host the REST calls go to. */
export function resolveSocketUrl(
  token: string,
  baseUrl: string = resolveBaseUrl(),
): string {
  const query = `token=${encodeURIComponent(token)}`;
  if (/^https?:\/\//i.test(baseUrl)) {
    const url = new URL(baseUrl);
    const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${url.host}/ws?${query}`;
  }
  const origin = window.location.origin.replace(/^http/i, (scheme) =>
    scheme.toLowerCase() === 'https' ? 'wss' : 'ws',
  );
  return `${origin}/ws?${query}`;
}

export function resolveBaseUrl(): string {
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

  socketUrl(token: string): string {
    return resolveSocketUrl(token, this.baseUrl);
  }

  listConversations(): Promise<Conversation[]> {
    return this.request('/conversations');
  }

  listMessages(
    conversationId: string,
    options: { beforeSeq?: number | null; afterSeq?: number | null; limit?: number } = {},
  ): Promise<MessagePage> {
    const params = new URLSearchParams();
    if (options.limit !== undefined) params.set('limit', String(options.limit));
    if (options.beforeSeq != null) params.set('before_seq', String(options.beforeSeq));
    if (options.afterSeq != null) params.set('after_seq', String(options.afterSeq));

    const query = params.toString();
    return this.request(
      `/conversations/${conversationId}/messages${query ? `?${query}` : ''}`,
    );
  }

  sendMessage(
    conversationId: string,
    input: { body: string; clientMsgId: string },
  ): Promise<ChatMessage> {
    return this.request(`/conversations/${conversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ body: input.body, client_msg_id: input.clientMsgId }),
    });
  }
}

export const api = new ApiClient();
