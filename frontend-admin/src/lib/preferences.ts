import type { DepartmentId, StudentPreferences, StudentRankings } from './types';

export const DEPARTMENTS: ReadonlyArray<{ id: DepartmentId; name: string }> = [
  { id: 'biomedical', name: 'Biomedical Engineering' },
  { id: 'chemical', name: 'Chemical Engineering' },
  { id: 'civil', name: 'Civil Engineering' },
  { id: 'computer', name: 'Computer Science and Engineering' },
  { id: 'electrical', name: 'Electrical Engineering' },
  { id: 'electronic', name: 'Electronic and Telecommunication Engineering' },
  { id: 'material', name: 'Materials Science and Engineering' },
  { id: 'mechanical', name: 'Mechanical Engineering' },
  { id: 'aeronautical', name: 'Aeronautical Engineering' },
  { id: 'mechatronics', name: 'Mechatronics Engineering' }
];

export function emptyRankings(): StudentRankings {
  return Object.fromEntries(DEPARTMENTS.map(({ id }) => [id, ''])) as StudentRankings;
}

export function validateRankings(rankings: StudentRankings): string | null {
  const values = DEPARTMENTS.map(({ id }) => rankings[id]);
  const rankCount = DEPARTMENTS.length;
  if (values.some((value) => value === '')) {
    return `Give every department a rank from 1 to ${rankCount}.`;
  }

  const ranks = values as number[];
  if (ranks.some((rank) => !Number.isInteger(rank) || rank < 1 || rank > rankCount)) {
    return `Ranks must be whole numbers from 1 to ${rankCount}.`;
  }
  if (new Set(ranks).size !== rankCount) {
    return `Each rank from 1 to ${rankCount} must be used once.`;
  }
  return null;
}

export function preferencesToRankings(preferences: StudentPreferences): StudentRankings {
  return Object.fromEntries(DEPARTMENTS.map(({ id }) => [id, preferences[id]])) as StudentRankings;
}

export function rankingsToPreferences(
  indexNumber: string,
  rankings: StudentRankings
): StudentPreferences {
  return {
    index_number: indexNumber,
    biomedical: Number(rankings.biomedical),
    chemical: Number(rankings.chemical),
    civil: Number(rankings.civil),
    computer: Number(rankings.computer),
    electrical: Number(rankings.electrical),
    electronic: Number(rankings.electronic),
    material: Number(rankings.material),
    mechanical: Number(rankings.mechanical),
    aeronautical: Number(rankings.aeronautical),
    mechatronics: Number(rankings.mechatronics)
  };
}
