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

export const POST_PREFERENCES_ROUTE = '/results';
