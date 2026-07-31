import type { ModuleGrade, ModuleGrades, StudentResults } from './types';

export const MODULE_GRADES: readonly ModuleGrade[] = [
  'A+',
  'A',
  'A-',
  'B+',
  'B',
  'B-',
  'C+',
  'C',
  'C-',
  'D',
  'F'
];

export function isModuleGrade(value: unknown): value is ModuleGrade {
  return typeof value === 'string' && MODULE_GRADES.includes(value as ModuleGrade);
}

export function isModuleGrades(value: unknown): value is ModuleGrades {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;

  const grades = value as Partial<ModuleGrades>;
  return isModuleGrade(grades.fluidMechanics) && isModuleGrade(grades.mechanics);
}

export const GRADE_TO_GPA: Record<ModuleGrade, number> = {
  'A+': 4,
  A: 4,
  'A-': 3.7,
  'B+': 3.3,
  B: 3,
  'B-': 2.7,
  'C+': 2.3,
  C: 2,
  'C-': 1.7,
  D: 1,
  F: 0
};

export function getGradeFromGpa(gpa: number | null | undefined): string {
  if (gpa == null) return 'Not available';
  if (gpa === 4) return 'A / A+';

  return MODULE_GRADES.find((grade) => GRADE_TO_GPA[grade] === gpa) ?? 'Not available';
}

export function hasSubmittedModuleGrades(results: StudentResults | null): boolean {
  return typeof results?.fluids === 'number' && typeof results.mechanics === 'number';
}
