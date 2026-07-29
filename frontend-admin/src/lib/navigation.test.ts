import { describe, expect, it } from 'vitest';
import { getStudentEntryRoute } from './navigation';

describe('student entry routing', () => {
  it('sends signed-out students to login', () => {
    expect(getStudentEntryRoute(false, false)).toBe('/login');
  });

  it('sends students missing either module grade to the grade form', () => {
    expect(getStudentEntryRoute(true, false)).toBe('/module-grades');
  });

  it('allows students with both module grades to open preferences', () => {
    expect(getStudentEntryRoute(true, true)).toBe('/preferences');
  });
});
