import type { SupabaseClient } from '@supabase/supabase-js';
import { describe, expect, it, vi } from 'vitest';
import {
  hasEditableSession,
  sendPreferenceOtp,
  signInWithPersonalPassword,
  verifyPreferenceOtp
} from './student-edit-auth';

function clientWith(auth: Record<string, unknown>): SupabaseClient {
  return { auth } as unknown as SupabaseClient;
}

const lookup = vi.fn().mockResolvedValue('student@example.test');

describe('student preference editing authentication', () => {
  it('uses the registered email for a personal-password login', async () => {
    const signInWithPassword = vi.fn().mockResolvedValue({ error: null });
    const result = await signInWithPersonalPassword(
      '220001a',
      'my-personal-password',
      lookup,
      clientWith({ signInWithPassword })
    );

    expect(result).toEqual({ ok: true });
    expect(lookup).toHaveBeenCalledWith('220001A');
    expect(signInWithPassword).toHaveBeenCalledWith({
      email: 'student@example.test',
      password: 'my-personal-password'
    });
  });

  it('does not reveal whether an invalid personal password or account caused login failure', async () => {
    const result = await signInWithPersonalPassword(
      '220001A',
      'wrong-password',
      lookup,
      clientWith({ signInWithPassword: vi.fn().mockResolvedValue({ error: new Error('bad credentials') }) })
    );
    expect(result).toEqual({ ok: false, message: 'Invalid index number or personal password.' });
  });

  it('sends an email OTP without displaying the email in its result', async () => {
    const signInWithOtp = vi.fn().mockResolvedValue({ error: null });
    const result = await sendPreferenceOtp('220001A', lookup, clientWith({ signInWithOtp }));
    expect(result).toEqual({ ok: true });
    expect(signInWithOtp).toHaveBeenCalledWith({ email: 'student@example.test' });
  });

  it('verifies the six-digit email OTP and establishes the Auth session before password creation', async () => {
    const verifyOtp = vi.fn().mockResolvedValue({ error: null });
    const result = await verifyPreferenceOtp(
      '220001A',
      '123456',
      lookup,
      clientWith({ verifyOtp })
    );
    expect(result).toEqual({ ok: true });
    expect(verifyOtp).toHaveBeenCalledWith({
      email: 'student@example.test',
      token: '123456',
      type: 'email'
    });
  });

  it('accepts edit access only when the current Auth user matches the entered index email', async () => {
    const matching = await hasEditableSession(
      '220001A',
      lookup,
      clientWith({ getUser: vi.fn().mockResolvedValue({ data: { user: { email: 'STUDENT@example.test' } }, error: null }) })
    );
    const nonMatching = await hasEditableSession(
      '220001A',
      lookup,
      clientWith({ getUser: vi.fn().mockResolvedValue({ data: { user: { email: 'other@example.test' } }, error: null }) })
    );
    expect(matching).toBe(true);
    expect(nonMatching).toBe(false);
  });
});
