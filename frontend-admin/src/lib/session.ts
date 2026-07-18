import type { StudentSession } from './types';

const SESSION_KEY = 'field-selection-student';

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
}

export function clearStudentSession(): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(SESSION_KEY);
}
