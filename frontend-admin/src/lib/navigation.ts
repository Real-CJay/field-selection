import { hasSubmittedModuleGrades } from './module-grades';
import type { StudentPreferences, StudentResults } from './types';

export type StudentEntryRoute = '/login' | '/module-grades' | '/preferences';
export type StudentResultsEntryRoute = StudentEntryRoute | '/results';

export function getStudentEntryRoute(
  hasSession: boolean,
  hasModuleGrades: boolean
): StudentEntryRoute {
  if (!hasSession) return '/login';
  return hasModuleGrades ? '/preferences' : '/module-grades';
}

export function getStudentResultsEntryRoute(
  hasSession: boolean,
  hasModuleGrades: boolean,
  hasPreferences: boolean
): StudentResultsEntryRoute {
  if (!hasSession) return '/login';
  if (!hasModuleGrades) return '/module-grades';
  return hasPreferences ? '/results' : '/preferences';
}

export async function getReturningStudentRoute(
  indexNumber: string,
  getResults: (indexNumber: string) => Promise<StudentResults | null>,
  getPreferences: (indexNumber: string) => Promise<StudentPreferences | null>
): Promise<StudentResultsEntryRoute> {
  const [results, preferences] = await Promise.all([
    getResults(indexNumber),
    getPreferences(indexNumber)
  ]);

  return getStudentResultsEntryRoute(
    true,
    hasSubmittedModuleGrades(results),
    Boolean(preferences)
  );
}

export const POST_PREFERENCES_ROUTE = '/results';
