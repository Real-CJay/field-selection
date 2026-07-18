import { describe, expect, it } from 'vitest';
import {
  DEPARTMENTS,
  emptyRankings,
  preferencesToRankings,
  rankingsToPreferences,
  validateRankings
} from './preferences';
import type { StudentPreferences, StudentRankings } from './types';

const validRankings = Object.fromEntries(
  DEPARTMENTS.map(({ id }, index) => [id, index + 1])
) as StudentRankings;

describe('preference rankings', () => {
  it('requires every department', () => {
    expect(validateRankings(emptyRankings())).toBe('Give every department a rank from 1 to 9.');
  });

  it('rejects duplicate ranks', () => {
    const duplicate = { ...validRankings, biomedical: 2 };
    expect(validateRankings(duplicate)).toBe('Each rank from 1 to 9 must be used once.');
  });

  it('accepts each rank from 1 to 9 exactly once', () => {
    expect(validateRankings(validRankings)).toBeNull();
  });

  it('creates the exact Supabase upsert payload', () => {
    expect(rankingsToPreferences('220001A', validRankings)).toEqual({
      index_number: '220001A',
      biomedical: 1,
      chemical: 2,
      computer: 3,
      electrical: 4,
      electronic: 5,
      material: 6,
      mechanical: 7,
      aeronautical: 8,
      mechatronics: 9
    });
  });

  it('loads stored preferences into the form', () => {
    const saved = {
      ...rankingsToPreferences('220001A', validRankings),
      submitted_at: '2026-07-18T00:00:00Z'
    } satisfies StudentPreferences;
    expect(preferencesToRankings(saved)).toEqual(validRankings);
  });
});
