import { describe, expect, it, vi } from 'vitest';
import {
  createStudentPassword,
  signInStudent,
  tokenFromLogin,
  verifyRecoveryCode
} from './student-auth-client';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });
}

describe('student recovery authentication client', () => {
  it('accepts an editable personal-password login response', async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({
      access_mode: 'editable',
      edit_token: 'edit.signed-token',
      index_number: '250544U',
      name: 'Student'
    }));
    const result = await signInStudent('250544U', 'personal password', fetcher);
    expect(tokenFromLogin(result)).toBe('edit.signed-token');
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      index_number: '250544U',
      password: 'personal password'
    });
  });

  it('sends only index and recovery code for setup verification', async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({
      password_setup_token: 'temporary-token',
      expires_in: 600
    }));
    await verifyRecoveryCode('250544U', '1234-5678-9012-3456', fetcher);
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      index_number: '250544U',
      recovery_code: '1234-5678-9012-3456'
    });
  });

  it('creates a password without sending index, email, or recovery code again', async () => {
    const fetcher = vi.fn().mockResolvedValue(jsonResponse({
      access_mode: 'editable',
      edit_token: 'edit.new-token',
      index_number: '250544U',
      name: 'Student'
    }));
    await createStudentPassword('setup-token', 'allowed1', 'allowed1', fetcher);
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      password_setup_token: 'setup-token',
      password: 'allowed1',
      password_confirmation: 'allowed1'
    });
  });
});
