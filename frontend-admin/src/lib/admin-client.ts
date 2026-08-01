import { env } from '$env/dynamic/public';
import { basicAuthorization } from './correction-client';
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

function headers(username: string, password: string): HeadersInit {
  return { Authorization: basicAuthorization(username, password) };
}

export async function authenticateAdmin(
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const response = await fetcher(`${baseUrl()}/api/admin/login`, {
    headers: headers(username, password)
  });
  if (!response.ok) throw new Error(await message(response));
}

export async function getAdminStudents(
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<AdminStudentRecord[]> {
  const response = await fetcher(`${baseUrl()}/api/admin/students`, {
    headers: headers(username, password)
  });
  if (!response.ok) throw new Error(await message(response));
  return (await response.json()).students;
}

export async function getAdminDepartments(
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<AdminDepartmentRecord[]> {
  const response = await fetcher(`${baseUrl()}/api/admin/departments`, {
    headers: headers(username, password)
  });
  if (!response.ok) throw new Error(await message(response));
  return (await response.json()).departments;
}

export async function updateAdminGrades(
  indexNumber: string,
  grades: Partial<Record<'cse' | 'maths' | 'electrical' | 'fluids' | 'mechanics' | 'material', ModuleGrade>>,
  username: string,
  password: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const response = await fetcher(
    `${baseUrl()}/api/admin/students/${encodeURIComponent(indexNumber)}/grades`,
    {
      method: 'PATCH',
      headers: {
        ...headers(username, password),
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(grades)
    }
  );
  if (!response.ok) throw new Error(await message(response));
}
