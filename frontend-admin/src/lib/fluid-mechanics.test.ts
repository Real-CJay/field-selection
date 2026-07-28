import { describe, expect, it } from 'vitest';
import { FLUID_MECHANICS_GRADES, isFluidMechanicsGrade } from './fluid-mechanics';

describe('Fluid Mechanics grades', () => {
  it('contains the allowed grades in display order', () => {
    expect(FLUID_MECHANICS_GRADES).toEqual([
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
    ]);
  });

  it('accepts only an allowed grade', () => {
    expect(isFluidMechanicsGrade('B+')).toBe(true);
    expect(isFluidMechanicsGrade('E')).toBe(false);
    expect(isFluidMechanicsGrade('')).toBe(false);
  });
});
