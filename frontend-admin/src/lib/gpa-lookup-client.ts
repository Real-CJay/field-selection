import { env } from '$env/dynamic/public';
import type { GpaLookupResult } from './types';

function baseUrl(): string {
  const value = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!value) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  return value;
}

async function errorMessage(response: Response): Promise<string> {
  try {
    return (await response.json()).detail ?? 'Unable to look up this GPA.';
  } catch {
    return 'Unable to look up this GPA.';
  }
}

export async function getAnonymousGpaLookup(
  gpa: string,
  fetcher: typeof fetch = fetch
): Promise<GpaLookupResult> {
  const response = await fetcher(
    `${baseUrl()}/api/gpa-lookup?gpa=${encodeURIComponent(gpa)}`
  );
  if (!response.ok) throw new Error(await errorMessage(response));
  return response.json();
}
