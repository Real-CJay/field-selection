import { env } from '$env/dynamic/public';
import type { StudentAccessMode } from './student-api-session';

export interface StudentIdentity {
  index_number: string;
  name: string;
}

export type StudentLoginResult = StudentIdentity & {
  access_mode: StudentAccessMode;
  read_token?: string;
  edit_token?: string;
};

export interface PasswordSetupChallenge {
  password_setup_token: string;
  expires_in: number;
}

function baseUrl(): string {
  const value = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!value) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  return value;
}

async function errorMessage(response: Response, fallback: string): Promise<string> {
  try {
    return (await response.json()).detail ?? fallback;
  } catch {
    return fallback;
  }
}

async function postJson<T>(
  path: string,
  body: unknown,
  fallback: string,
  fetcher: typeof fetch
): Promise<T> {
  const response = await fetcher(`${baseUrl()}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(await errorMessage(response, fallback));
  return await response.json() as T;
}

export async function signInStudent(
  indexNumber: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<StudentLoginResult> {
  const response = await fetcher(`${baseUrl()}/api/student/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ index_number: indexNumber, password })
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Invalid index number or password.'));
  }
  return await response.json();
}

export async function verifyRecoveryCode(
  indexNumber: string,
  recoveryCode: string,
  fetcher: typeof fetch = fetch
): Promise<PasswordSetupChallenge> {
  return postJson(
    '/api/student/auth/recovery/verify',
    { index_number: indexNumber, recovery_code: recoveryCode },
    'Invalid index number or recovery code.',
    fetcher
  );
}

export async function createStudentPassword(
  setupToken: string,
  password: string,
  passwordConfirmation: string,
  fetcher: typeof fetch = fetch
): Promise<StudentLoginResult> {
  return postJson(
    '/api/student/auth/password',
    {
      password_setup_token: setupToken,
      password,
      password_confirmation: passwordConfirmation
    },
    'Unable to create the personal password.',
    fetcher
  );
}

export function tokenFromLogin(result: StudentLoginResult): string {
  const token = result.access_mode === 'editable' ? result.edit_token : result.read_token;
  if (!token) throw new Error('The server did not return a valid student session.');
  return token;
}
