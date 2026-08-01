import { afterEach, describe, expect, it } from 'vitest';
import {
  clearAdminCredentials,
  getAdminCredentials,
  setAdminCredentials
} from './admin-session';

describe('admin session', () => {
  afterEach(clearAdminCredentials);

  it('keeps credentials only in the current in-memory session', () => {
    expect(getAdminCredentials()).toBeNull();
    setAdminCredentials({ username: 'CJay', password: 'test-password' });
    expect(getAdminCredentials()).toEqual({ username: 'CJay', password: 'test-password' });
    clearAdminCredentials();
    expect(getAdminCredentials()).toBeNull();
  });
});
