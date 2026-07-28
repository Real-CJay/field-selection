import type { FluidMechanicsGrade } from './types';

export const FLUID_MECHANICS_GRADES: readonly FluidMechanicsGrade[] = [
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

export function isFluidMechanicsGrade(value: unknown): value is FluidMechanicsGrade {
  return (
    typeof value === 'string' &&
    FLUID_MECHANICS_GRADES.includes(value as FluidMechanicsGrade)
  );
}
