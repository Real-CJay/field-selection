import { env } from '$env/dynamic/public';
import type { CorrectableModule, GradeCorrectionRequest, ModuleGrade } from './types';

function apiBaseUrl(): string {
  const value = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!value) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  return value;
}

async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    return body.detail ?? 'The request could not be completed.';
  } catch {
    return 'The request could not be completed.';
  }
}

export async function submitGradeCorrection(
  module: CorrectableModule,
  requestedGrade: ModuleGrade,
  accessToken: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const response = await fetcher(`${apiBaseUrl()}/api/correction-requests`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ module, requested_grade: requestedGrade })
  });
  if (!response.ok) throw new Error(await readError(response));
}

export function basicAuthorization(username: string, password: string): string {
  return `Basic ${btoa(`${username}:${password}`)}`;
}

export async function getCorrectionRequests(
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<GradeCorrectionRequest[]> {
  const response = await fetcher(`${apiBaseUrl()}/api/admin/correction-requests`, {
    headers: { Authorization: basicAuthorization(username, password) }
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()).requests;
}

export async function reviewCorrectionRequest(
  id: number,
  decision: 'approved' | 'rejected',
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const response = await fetcher(`${apiBaseUrl()}/api/admin/correction-requests/${id}`, {
    method: 'PATCH',
    headers: {
      Authorization: basicAuthorization(username, password),
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ decision })
  });
  if (!response.ok) throw new Error(await readError(response));
}


export async function revertCorrectionRequest(
  id: number,
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const response = await fetcher(`${apiBaseUrl()}/api/admin/correction-requests/${id}/revert`, {
    method: 'POST',
    headers: { Authorization: basicAuthorization(username, password) }
  });
  if (!response.ok) throw new Error(await readError(response));
}
