import { isModuleGrades } from './module-grades';
import type { ModuleGrades, StudentSession } from './types';

const SESSION_KEY = 'field-selection-student';
const MODULE_GRADES_KEY = 'field-selection-module-grades';

export function getStudentSession(): StudentSession | null {
  if (typeof sessionStorage === 'undefined') return null;

  const saved = sessionStorage.getItem(SESSION_KEY);
  if (!saved) return null;

  try {
    const parsed = JSON.parse(saved) as Partial<StudentSession>;
    if (typeof parsed.indexNumber !== 'string' || typeof parsed.name !== 'string') {
      sessionStorage.removeItem(SESSION_KEY);
      return null;
    }
    return { indexNumber: parsed.indexNumber, name: parsed.name };
  } catch {
    sessionStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export function saveStudentSession(session: StudentSession): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  sessionStorage.removeItem(MODULE_GRADES_KEY);
}

export function getModuleGrades(): ModuleGrades | null {
  if (typeof sessionStorage === 'undefined') return null;

  const saved = sessionStorage.getItem(MODULE_GRADES_KEY);
  if (!saved) return null;

  try {
    const parsed: unknown = JSON.parse(saved);
    if (!isModuleGrades(parsed)) {
      sessionStorage.removeItem(MODULE_GRADES_KEY);
      return null;
    }
    return parsed;
  } catch {
    sessionStorage.removeItem(MODULE_GRADES_KEY);
    return null;
  }
}

export function saveModuleGrades(grades: ModuleGrades): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(MODULE_GRADES_KEY, JSON.stringify(grades));
}

export function clearStudentSession(): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(MODULE_GRADES_KEY);
}
