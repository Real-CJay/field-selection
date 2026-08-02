import { describe, expect, it, vi } from 'vitest';
import { authenticateAdmin } from './admin-client';

describe('admin authentication client', () => {
  it('sends the CJay credentials to the protected backend login endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response('{}', { status: 200 }));

    await authenticateAdmin('CJay', 'admin-password', fetcher);

    expect(fetcher).toHaveBeenCalledOnce();
    const [url, options] = fetcher.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/admin\/login$/);
    expect(options.headers.Authorization).toBe(`Basic ${btoa('CJay:admin-password')}`);
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
