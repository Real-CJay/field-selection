import { env } from '$env/dynamic/public';

export interface StudentIdentity {
  index_number: string;
  name: string;
}

export type StudentLoginResult = StudentIdentity & {
  access_mode: 'read-only';
  read_token: string;
};

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

export async function signInStudent(
  indexNumber: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<StudentLoginResult> {
  const response = await fetcher(`${baseUrl()}/api/student/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      index_number: indexNumber,
      password
    })
  });
  if (!response.ok) {
    throw new Error(await errorMessage(response, 'Invalid index number or password.'));
  }
  return await response.json();
}
