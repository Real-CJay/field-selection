import { describe, expect, it } from 'vitest';
import {
  GRADE_TO_GPA,
  MODULE_GRADES,
  getEditableGradeFromGpa,
  getGradeFromGpa,
  isModuleGrade,
  isModuleGrades,
  hasSubmittedModuleGrades
} from './module-grades';

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

  it('converts letter grades to stored grade points and back', () => {
    expect(GRADE_TO_GPA['A-']).toBe(3.7);
    expect(GRADE_TO_GPA.F).toBe(0);
    expect(getGradeFromGpa(3.7)).toBe('A-');
    expect(getGradeFromGpa(4)).toBe('A / A+');
    expect(getEditableGradeFromGpa(3.7)).toBe('A-');
  });
});

describe('submitted module grades', () => {
  it('requires both Fluid Mechanics and Mechanics results', () => {
    expect(hasSubmittedModuleGrades({ index_number: '220001A', fluids: 3.7, mechanics: 3.3 })).toBe(
      true
    );
    expect(hasSubmittedModuleGrades({ index_number: '220001A', fluids: 3.7 })).toBe(false);
    expect(hasSubmittedModuleGrades(null)).toBe(false);
  });
});
