import { describe, expect, it } from 'vitest';
import { MODULE_GRADES, isModuleGrade, isModuleGrades } from './module-grades';

describe('module grades', () => {
  it('contains the allowed grades in display order', () => {
    expect(MODULE_GRADES).toEqual([
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

  it('accepts only an allowed individual grade', () => {
    expect(isModuleGrade('B+')).toBe(true);
    expect(isModuleGrade('E')).toBe(false);
    expect(isModuleGrade('')).toBe(false);
  });

  it('requires valid Fluid Mechanics and Mechanics grades', () => {
    expect(isModuleGrades({ fluidMechanics: 'A-', mechanics: 'B+' })).toBe(true);
    expect(isModuleGrades({ fluidMechanics: 'A-', mechanics: '' })).toBe(false);
    expect(isModuleGrades({ fluidMechanics: 'E', mechanics: 'B+' })).toBe(false);
    expect(isModuleGrades({ fluidMechanics: 'A-' })).toBe(false);
  });
});
