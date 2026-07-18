import { STUDENT_PASSWORD } from './credentials';
import type { Student } from './types';

type StudentLookup = (indexNumber: string) => Promise<Student | null>;

export type LoginResult =
  | { ok: true; student: Student }
  | { ok: false; message: string };

export function normalizeIndexNumber(value: string): string {
  return value.trim().toUpperCase();
}

export async function authenticateStudent(
  indexNumber: string,
  password: string,
  findStudent: StudentLookup
): Promise<LoginResult> {
  const normalizedIndex = normalizeIndexNumber(indexNumber);

  if (!normalizedIndex) return { ok: false, message: 'Enter your index number.' };
  if (password !== STUDENT_PASSWORD) return { ok: false, message: 'Incorrect password.' };

  try {
    const student = await findStudent(normalizedIndex);
    if (!student) return { ok: false, message: 'Student index number was not found.' };
    return { ok: true, student };
  } catch {
    return { ok: false, message: 'Unable to check the student record. Please try again.' };
  }
}
