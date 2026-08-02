import { env } from '$env/dynamic/public';

export interface StudentIdentity {
  index_number: string;
  name: string;
}

export interface StudentAuthTokens {
  access_token: string;
  refresh_token: string;
  expires_at: number | null;
  token_type: string;
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

export async function requestStudentMagicLink(
  indexNumber: string,
  turnstileToken: string,
  fetcher: typeof fetch = fetch
): Promise<string> {
  const response = await fetcher(`${baseUrl()}/api/student/auth/magic-link`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ index_number: indexNumber, turnstile_token: turnstileToken })
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Unable to send the confirmation email.'));
  }
  return (await response.json()).message;
}

export async function signInStudentWithPassword(
  indexNumber: string,
  password: string,
  turnstileToken: string,
  fetcher: typeof fetch = fetch
): Promise<StudentAuthTokens> {
  const response = await fetcher(`${baseUrl()}/api/student/auth/password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      index_number: indexNumber,
      password,
      turnstile_token: turnstileToken
    })
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Invalid index number or personal password.'));
  }
  return await response.json();
}

export async function getAuthenticatedStudent(
  accessToken: string,
  fetcher: typeof fetch = fetch
): Promise<StudentIdentity> {
  const response = await fetcher(`${baseUrl()}/api/student/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` }
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Unable to verify the student account.'));
  }
  return await response.json();
}
