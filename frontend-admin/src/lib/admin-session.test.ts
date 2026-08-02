import { afterEach, describe, expect, it } from 'vitest';
import {
  clearAdminSession,
  getAdminSession,
  setAdminSession
} from './admin-session';

describe('admin session', () => {
  afterEach(clearAdminSession);

  it('keeps only the signed token in the current in-memory session', () => {
    expect(getAdminSession()).toBeNull();
    setAdminSession({ username: 'CJay', token: 'signed-token' });
    expect(getAdminSession()).toEqual({ username: 'CJay', token: 'signed-token' });
    clearAdminSession();
    expect(getAdminSession()).toBeNull();
  });
});
