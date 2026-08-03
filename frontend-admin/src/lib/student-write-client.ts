import { env } from '$env/dynamic/public';
import { getStudentApiToken, getStudentEditToken } from './student-api-session';
import type {
  CorrectableModule,
  ModuleGrades,
  ModuleGrade,
  StudentPreferences,
  StudentRankings
} from './types';

function baseUrl(): string {
  const value = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!value) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  return value;
}

export class StudentWriteError extends Error {
  constructor(message: string, public readonly status: number) {
    super(message);
  }
}

export interface StudentWriteStatus {
  enabled: boolean;
  personalPasswordSet: boolean;
}

export function isStudentWriteAuthError(error: unknown): boolean {
  return error instanceof StudentWriteError && (error.status === 401 || error.status === 403);
}

async function errorMessage(response: Response, fallback: string): Promise<string> {
  try {
    return (await response.json()).detail ?? fallback;
  } catch {
    return fallback;
  }
}

async function authorizedRequest<T>(
  path: string,
  method: 'POST' | 'PUT' | 'PATCH',
  body: unknown,
  fallback: string
): Promise<T> {
  const token = await getStudentEditToken();
  const response = await fetch(`${baseUrl()}${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new StudentWriteError(await errorMessage(response, fallback), response.status);
  return await response.json() as T;
}

export async function getStudentWriteStatus(): Promise<StudentWriteStatus> {
  const token = await getStudentApiToken();
  const response = await fetch(`${baseUrl()}/api/student/writes/status`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) throw new StudentWriteError(
    await errorMessage(response, 'Unable to check student editing availability.'),
    response.status
  );
  const result = await response.json();
  return {
    enabled: Boolean(result.enabled),
    personalPasswordSet: Boolean(result.personal_password_set)
  };
}

export async function saveStudentPreferences(
  rankings: StudentRankings
): Promise<StudentPreferences> {
  const result = await authorizedRequest<{ preferences: StudentPreferences }>(
    '/api/student/preferences',
    'PUT',
    rankings,
    'Unable to save preferences.'
  );
  return result.preferences;
}

export async function saveStudentModuleGrades(grades: ModuleGrades): Promise<number> {
  const result = await authorizedRequest<{ average_gpa: number }>(
    '/api/student/results',
    'PATCH',
    { fluids: grades.fluidMechanics, mechanics: grades.mechanics },
    'Unable to save module grades.'
  );
  return result.average_gpa;
}

export async function submitStudentCorrection(
  module: CorrectableModule,
  requestedGrade: ModuleGrade
): Promise<void> {
  await authorizedRequest(
    '/api/correction-requests',
    'POST',
    { module, requested_grade: requestedGrade },
    'Unable to send the correction request.'
  );
}
