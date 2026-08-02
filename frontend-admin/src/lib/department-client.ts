import { env } from '$env/dynamic/public';
import type { DepartmentGpaGroup, DepartmentId } from './types';
import { getStudentApiToken } from './student-api-session';

export async function getDepartmentGpas(
  department: DepartmentId,
  fetcher: typeof fetch = fetch
): Promise<{ groups: DepartmentGpaGroup[]; incomplete: boolean; minimumGroupSize: number }> {
  const baseUrl = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!baseUrl) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  const token = await getStudentApiToken();
  const response = await fetcher(
    `${baseUrl}/api/departments/${encodeURIComponent(department)}/gpas`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!response.ok) throw new Error('Unable to load department GPA information.');
  const body = await response.json();
  return {
    groups: body.groups,
    incomplete: body.incomplete,
    minimumGroupSize: body.minimum_group_size
  };
}
