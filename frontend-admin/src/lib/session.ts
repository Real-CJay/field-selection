import { isFluidMechanicsGrade } from './fluid-mechanics';
import type { FluidMechanicsGrade, StudentSession } from './types';

const SESSION_KEY = 'field-selection-student';
const FLUID_MECHANICS_GRADE_KEY = 'field-selection-fluid-mechanics-grade';

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
  sessionStorage.removeItem(FLUID_MECHANICS_GRADE_KEY);
}

export function getFluidMechanicsGrade(): FluidMechanicsGrade | null {
  if (typeof sessionStorage === 'undefined') return null;

  const saved = sessionStorage.getItem(FLUID_MECHANICS_GRADE_KEY);
  if (!isFluidMechanicsGrade(saved)) {
    sessionStorage.removeItem(FLUID_MECHANICS_GRADE_KEY);
    return null;
  }
  return saved;
}

export function saveFluidMechanicsGrade(grade: FluidMechanicsGrade): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(FLUID_MECHANICS_GRADE_KEY, grade);
}

export function clearStudentSession(): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(FLUID_MECHANICS_GRADE_KEY);
}
