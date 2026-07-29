import type { ModuleGrade, ModuleGrades } from './types';

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
