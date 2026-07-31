import { isModuleGrades } from './module-grades';
import type { ModuleGrades, StudentSession } from './types';

const SESSION_KEY = 'field-selection-student';
const MODULE_GRADES_KEY = 'field-selection-module-grades';

export function getStudentSession(): StudentSession | null {
  if (typeof localStorage === 'undefined') return null;

  const saved = localStorage.getItem(SESSION_KEY);
  if (!saved) return null;

  try {
    const parsed = JSON.parse(saved) as Partial<StudentSession>;
    if (typeof parsed.indexNumber !== 'string' || typeof parsed.name !== 'string') {
      localStorage.removeItem(SESSION_KEY);
      return null;
    }
    return { indexNumber: parsed.indexNumber, name: parsed.name };
  } catch {
    localStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function saveStudentSession(session: StudentSession): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  localStorage.removeItem(MODULE_GRADES_KEY);
}

export function getModuleGrades(): ModuleGrades | null {
  if (typeof localStorage === 'undefined') return null;

  const saved = localStorage.getItem(MODULE_GRADES_KEY);
  if (!saved) return null;

  try {
    const parsed: unknown = JSON.parse(saved);
    if (!isModuleGrades(parsed)) {
      localStorage.removeItem(MODULE_GRADES_KEY);
      return null;
    }
    return parsed;
  } catch {
    localStorage.removeItem(MODULE_GRADES_KEY);
    return null;
  }
}

export function saveModuleGrades(grades: ModuleGrades): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.setItem(MODULE_GRADES_KEY, JSON.stringify(grades));
}

export function clearStudentSession(): void {
  if (typeof localStorage === 'undefined') return;
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(MODULE_GRADES_KEY);
}
