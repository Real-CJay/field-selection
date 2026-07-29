export type StudentEntryRoute = '/login' | '/module-grades' | '/preferences';

export function getStudentEntryRoute(
  hasSession: boolean,
  hasModuleGrades: boolean
): StudentEntryRoute {
  if (!hasSession) return '/login';
  return hasModuleGrades ? '/preferences' : '/module-grades';
}
