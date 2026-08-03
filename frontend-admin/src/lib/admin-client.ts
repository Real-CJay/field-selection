import { env } from '$env/dynamic/public';
import type { AdminDepartmentRecord, AdminStudentRecord, ModuleGrade } from './types';

function baseUrl(): string {
  const value = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!value) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  return value;
}

async function message(response: Response): Promise<string> {
  try {
    return (await response.json()).detail ?? 'The admin request failed.';
  } catch {
    return 'The admin request failed.';
  }
}

function headers(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}` };
}

export async function authenticateAdmin(
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<{ username: string; admin_token: string }> {
  const response = await fetcher(`${baseUrl()}/api/admin/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });
  if (!response.ok) throw new Error(await message(response));
  return await response.json();
}

export async function getAdminStudents(
  token: string,
  fetcher: typeof fetch = fetch
): Promise<AdminStudentRecord[]> {
  const response = await fetcher(`${baseUrl()}/api/admin/students`, {
    headers: headers(token)
  });
  if (!response.ok) throw new Error(await message(response));
  return (await response.json()).students;
}

export async function getAdminDepartments(
  token: string,
  fetcher: typeof fetch = fetch
): Promise<AdminDepartmentRecord[]> {
  const response = await fetcher(`${baseUrl()}/api/admin/departments`, {
    headers: headers(token)
  });
  if (!response.ok) throw new Error(await message(response));
  return (await response.json()).departments;
}

export async function updateAdminGrades(
  indexNumber: string,
  grades: Partial<Record<'cse' | 'maths' | 'electrical' | 'fluids' | 'mechanics' | 'material', ModuleGrade>>,
  token: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const response = await fetcher(
    `${baseUrl()}/api/admin/students/${encodeURIComponent(indexNumber)}/grades`,
    {
      method: 'PATCH',
      headers: {
        ...headers(token),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(grades)
    }
  );
  if (!response.ok) throw new Error(await message(response));
}
