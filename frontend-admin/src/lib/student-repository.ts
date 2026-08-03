import { env } from '$env/dynamic/public';
import type { SupabaseClient } from '@supabase/supabase-js';
import { getStudentApiToken } from './student-api-session';
import { supabase } from './supabase';
import type { Student, StudentPreferences, StudentResults } from './types';

interface StudentRecord extends Student {
  results: StudentResults | null;
  preferences: StudentPreferences | null;
}

function baseUrl(): string {
  const value = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!value) throw new Error('PUBLIC_API_BASE_URL is not configured.');
  return value;
}

async function loadRecord(indexNumber: string, fetcher: typeof fetch = fetch): Promise<StudentRecord> {
  const token = await getStudentApiToken();
  const response = await fetcher(`${baseUrl()}/api/student/record`, {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (!response.ok) throw new Error('Unable to load the student record.');
  const record = await response.json() as StudentRecord;
  if (record.index_number.trim().toUpperCase() !== indexNumber.trim().toUpperCase()) {
    throw new Error('Student identity mismatch.');
  }
  return record;
}

export function createStudentRepository(
  client: SupabaseClient,
  recordLoader: (indexNumber: string) => Promise<StudentRecord> = loadRecord
) {
  return {
    async findStudent(indexNumber: string): Promise<Student | null> {
      const record = await recordLoader(indexNumber);
      return { index_number: record.index_number, name: record.name };
    },

    async getPreferences(indexNumber: string): Promise<StudentPreferences | null> {
      return (await recordLoader(indexNumber)).preferences;
    },

    async getResults(indexNumber: string): Promise<StudentResults | null> {
      return (await recordLoader(indexNumber)).results;
    },

    async savePreferences(preferences: StudentPreferences): Promise<void> {
      const { error } = await client
        .from('student_preferences')
        .upsert(preferences, { onConflict: 'index_number' });
      if (error) throw error;
    },

    async saveGrades(indexNumber: string, fluids: number, mechanics: number): Promise<void> {
      const { error } = await client
        .from('student_results')
        .upsert({ index_number: indexNumber, fluids, mechanics }, { onConflict: 'index_number' });
      if (error) throw error;
    }
  };
}

export const studentRepository = createStudentRepository(supabase);
