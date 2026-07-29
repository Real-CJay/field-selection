import { beforeEach, describe, expect, it } from 'vitest';
import {
  clearStudentSession,
  getModuleGrades,
  getStudentSession,
  saveModuleGrades,
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
    saveModuleGrades({ fluidMechanics: 'A-', mechanics: 'B+' });
    clearStudentSession();
    expect(getStudentSession()).toBeNull();
    expect(getModuleGrades()).toBeNull();
  });

  it('rejects malformed session data', () => {
    sessionStorage.setItem('field-selection-student', '{bad json');
    expect(getStudentSession()).toBeNull();
  });

  it('saves and restores both temporary module grades', () => {
    const grades = { fluidMechanics: 'B+' as const, mechanics: 'A-' as const };
    saveModuleGrades(grades);
    expect(getModuleGrades()).toEqual(grades);
  });

  it('clears old module grades when a student logs in', () => {
    saveModuleGrades({ fluidMechanics: 'C', mechanics: 'B' });
    saveStudentSession({ indexNumber: '220001A', name: 'Test Student' });
    expect(getModuleGrades()).toBeNull();
  });

  it('rejects missing or unsupported module grades', () => {
    sessionStorage.setItem(
      'field-selection-module-grades',
      JSON.stringify({ fluidMechanics: 'A', mechanics: 'E' })
    );
    expect(getModuleGrades()).toBeNull();

    sessionStorage.setItem(
      'field-selection-module-grades',
      JSON.stringify({ fluidMechanics: 'A' })
    );
    expect(getModuleGrades()).toBeNull();
  });
});
