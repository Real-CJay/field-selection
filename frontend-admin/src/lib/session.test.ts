import { beforeEach, describe, expect, it } from 'vitest';
import { clearStudentSession, getStudentSession, saveStudentSession } from './session';

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

describe('student session', () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, 'sessionStorage', {
      configurable: true,
      value: memoryStorage()
    });
  });

  it('saves and restores a student session', () => {
    const session = { indexNumber: '220001A', name: 'Test Student' };
    saveStudentSession(session);
    expect(getStudentSession()).toEqual(session);
  });

  it('clears a student session on logout', () => {
    saveStudentSession({ indexNumber: '220001A', name: 'Test Student' });
    clearStudentSession();
    expect(getStudentSession()).toBeNull();
  });

  it('rejects malformed session data', () => {
    sessionStorage.setItem('field-selection-student', '{bad json');
    expect(getStudentSession()).toBeNull();
  });
});
