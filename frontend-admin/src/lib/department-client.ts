import { env } from '$env/dynamic/public';
import type { DepartmentGpaGroup, DepartmentId } from './types';

export async function getDepartmentGpas(
  department: DepartmentId,
  fetcher: typeof fetch = fetch
): Promise<{ groups: DepartmentGpaGroup[]; incomplete: boolean }> {
  const baseUrl = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!baseUrl) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  const response = await fetcher(
    `${baseUrl}/api/departments/${encodeURIComponent(department)}/gpas`
  );
  if (!response.ok) throw new Error('Unable to load department GPA information.');
  const body = await response.json();
  return { groups: body.groups, incomplete: body.incomplete };
}
