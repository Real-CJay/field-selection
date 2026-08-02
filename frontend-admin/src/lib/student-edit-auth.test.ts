import type { SupabaseClient } from '@supabase/supabase-js';
import { describe, expect, it, vi } from 'vitest';
import { hasEditableSession, signOutStudentAuth } from './student-edit-auth';

function clientWith(auth: Record<string, unknown>): SupabaseClient {
  return { auth } as unknown as SupabaseClient;
}

describe('student write authentication', () => {
  it('accepts edit access only when a valid Auth session belongs to the entered index', async () => {
    const client = clientWith({
      getSession: vi.fn().mockResolvedValue({
        data: { session: { access_token: 'verified-token' } },
        error: null
      }),
      getUser: vi.fn().mockResolvedValue({ data: { user: { id: 'user-1' } }, error: null })
    });

    await expect(hasEditableSession(
      '220001A',
      client,
      vi.fn().mockResolvedValue({ index_number: '220001A', name: 'Student A' })
    )).resolves.toBe(true);

    await expect(hasEditableSession(
      '220001A',
      client,
      vi.fn().mockResolvedValue({ index_number: '220002B', name: 'Student B' })
    )).resolves.toBe(false);
  });

  it('rejects edit access when there is no Supabase session', async () => {
    const identityLookup = vi.fn();
    const client = clientWith({
      getSession: vi.fn().mockResolvedValue({ data: { session: null }, error: null })
    });
    await expect(hasEditableSession('220001A', client, identityLookup)).resolves.toBe(false);
    expect(identityLookup).not.toHaveBeenCalled();
  });

  it('signs out through Supabase Auth', async () => {
    const signOut = vi.fn().mockResolvedValue({ error: null });
    await signOutStudentAuth(clientWith({ signOut }));
    expect(signOut).toHaveBeenCalledOnce();
  });
});
