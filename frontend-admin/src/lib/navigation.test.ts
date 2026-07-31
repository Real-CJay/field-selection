import { describe, expect, it } from 'vitest';
import {
  POST_PREFERENCES_ROUTE,
  getStudentEntryRoute,
  getStudentResultsEntryRoute,
  getReturningStudentRoute
} from './navigation';

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

describe('results routing', () => {
  it('protects results in login, grade, and preference order', () => {
    expect(getStudentResultsEntryRoute(false, false, false)).toBe('/login');
    expect(getStudentResultsEntryRoute(true, false, false)).toBe('/module-grades');
    expect(getStudentResultsEntryRoute(true, true, false)).toBe('/preferences');
    expect(getStudentResultsEntryRoute(true, true, true)).toBe('/results');
  });

  it('sends a successful preference submission to results', () => {
    expect(POST_PREFERENCES_ROUTE).toBe('/results');
  });

  it('returns a previously completed student directly to results', async () => {
    await expect(
      getReturningStudentRoute(
        '220001A',
        async () => ({ index_number: '220001A', fluids: 3.7, mechanics: 3.3 }),
        async () =>
          ({ index_number: '220001A' }) as Awaited<
            ReturnType<Parameters<typeof getReturningStudentRoute>[2]>
          >
      )
    ).resolves.toBe('/results');
  });
});
