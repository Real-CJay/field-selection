import { describe, expect, it, vi } from 'vitest';
import { authenticateAdmin } from './admin-client';

describe('admin authentication client', () => {
  it('sends the CJay credentials to the protected backend login endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ username: 'CJay', admin_token: 'signed-token' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    ));

    await expect(authenticateAdmin('CJay', 'admin-password', fetcher))
      .resolves.toEqual({ username: 'CJay', admin_token: 'signed-token' });

    expect(fetcher).toHaveBeenCalledOnce();
    const [url, options] = fetcher.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/admin\/login$/);
    expect(JSON.parse(options.body)).toEqual({
      username: 'CJay',
      password: 'admin-password'
    });
    expect(options.headers.Authorization).toBeUndefined();
  });

  it('returns the backend admin error without attempting student authentication', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Invalid administrator credentials.' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    ));

    await expect(authenticateAdmin('CJay', 'wrong-password', fetcher)).rejects.toThrow(
      'Invalid administrator credentials.'
    );
  });
});
