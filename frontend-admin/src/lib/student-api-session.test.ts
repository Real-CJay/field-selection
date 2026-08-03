import { beforeEach, describe, expect, it } from 'vitest';
import {
  clearStudentReadToken,
  getStudentApiToken,
  getStudentReadToken,
  saveStudentReadToken
} from './student-api-session';

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() { return values.size; },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => { values.delete(key); },
    setItem: (key, value) => { values.set(key, value); }
  };
}

describe('student API session', () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, 'sessionStorage', {
      configurable: true,
      value: memoryStorage()
    });
  });

  it('survives a page-level module reload through session storage', async () => {
    saveStudentReadToken('read.signed-token');
    expect(getStudentReadToken()).toBe('read.signed-token');
    await expect(getStudentApiToken()).resolves.toBe('read.signed-token');
  });

  it('clears the token on logout', async () => {
    saveStudentReadToken('read.signed-token');
    clearStudentReadToken();
    expect(getStudentReadToken()).toBeNull();
    await expect(getStudentApiToken()).rejects.toThrow('secure session has expired');
  });
});
