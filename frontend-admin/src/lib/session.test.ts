import { beforeEach, describe, expect, it } from 'vitest';
import {
  clearStudentSession,
  getFluidMechanicsGrade,
  getStudentSession,
  saveFluidMechanicsGrade,
  saveStudentSession
} from './session';

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
    saveFluidMechanicsGrade('A-');
    clearStudentSession();
    expect(getStudentSession()).toBeNull();
    expect(getFluidMechanicsGrade()).toBeNull();
  });

  it('rejects malformed session data', () => {
    sessionStorage.setItem('field-selection-student', '{bad json');
    expect(getStudentSession()).toBeNull();
  });

  it('saves and restores the temporary Fluid Mechanics grade', () => {
    saveFluidMechanicsGrade('B+');
    expect(getFluidMechanicsGrade()).toBe('B+');
  });

  it('clears an old grade when a student logs in', () => {
    saveFluidMechanicsGrade('C');
    saveStudentSession({ indexNumber: '220001A', name: 'Test Student' });
    expect(getFluidMechanicsGrade()).toBeNull();
  });

  it('rejects a grade outside the allowed list', () => {
    sessionStorage.setItem('field-selection-fluid-mechanics-grade', 'E');
    expect(getFluidMechanicsGrade()).toBeNull();
  });
});
