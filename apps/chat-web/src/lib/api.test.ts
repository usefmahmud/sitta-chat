import { describe, expect, it, vi } from 'vitest';

import { ApiClient, ApiError } from './api';

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const AUTH_BODY = {
  access_token: 'token-123',
  token_type: 'bearer',
  expires_in: 3600,
  user: {
    id: 'u-1',
    email: 'omar@example.com',
    display_name: 'Omar',
    created_at: '2026-01-01T00:00:00Z',
  },
};

describe('ApiClient', () => {
  it('posts credentials and returns the auth payload', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, AUTH_BODY));
    const api = new ApiClient({ baseUrl: '/api', fetchImpl });

    const result = await api.login({ email: 'omar@example.com', password: 'pass12345' });

    expect(result.access_token).toBe('token-123');
    const [url, init] = fetchImpl.mock.calls[0];
    expect(url).toBe('/api/auth/login');
    expect(init.method).toBe('POST');
    expect(JSON.parse(init.body)).toEqual({
      email: 'omar@example.com',
      password: 'pass12345',
    });
  });

  it('sends the in-memory token as a bearer header', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(200, AUTH_BODY.user));
    const api = new ApiClient({ baseUrl: '/api', getToken: () => 'token-123', fetchImpl });

    await api.me();

    const headers = fetchImpl.mock.calls[0][1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer token-123');
  });

  it('clears the session on 401 and does not retry', async () => {
    const onUnauthorized = vi.fn();
    const fetchImpl = vi.fn().mockResolvedValue(jsonResponse(401, { detail: 'invalid' }));
    const api = new ApiClient({
      baseUrl: '/api',
      getToken: () => 'dead-token',
      onUnauthorized,
      fetchImpl,
    });

    await expect(api.me()).rejects.toBeInstanceOf(ApiError);
    await expect(api.me()).rejects.toMatchObject({ status: 401, code: 'unauthorized' });

    expect(onUnauthorized).toHaveBeenCalledTimes(2);
    expect(fetchImpl).toHaveBeenCalledTimes(2);
  });

  it('maps a rejected fetch to a network error', async () => {
    const fetchImpl = vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));
    const api = new ApiClient({ baseUrl: '/api', fetchImpl });

    await expect(api.login({ email: 'x@y.dev', password: 'pass12345' })).rejects.toMatchObject({
      code: 'network',
      status: 0,
    });
  });

  it('turns a 409 into a conflict carrying the server detail', async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(jsonResponse(409, { detail: 'email already registered' }));
    const api = new ApiClient({ baseUrl: '/api', fetchImpl });

    await expect(
      api.register({ email: 'x@y.dev', password: 'pass12345', display_name: 'X' }),
    ).rejects.toMatchObject({
      status: 409,
      code: 'conflict',
      message: 'email already registered',
    });
  });
});
