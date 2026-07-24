import type { SupabaseClient } from '@supabase/supabase-js';
import { supabase } from './supabase';
import type { Student, StudentPreferences } from './types';

export function createStudentRepository(client: SupabaseClient) {
  return {
    async findStudent(indexNumber: string): Promise<Student | null> {
      const { data, error } = await client
        .from('students')
        .select('index_number, name, email')
        .eq('index_number', indexNumber)
        .maybeSingle();

      if (error) throw error;
      return data as Student | null;
    },

    async getPreferences(indexNumber: string): Promise<StudentPreferences | null> {
      const { data, error } = await client
        .from('student_preferences')
        .select(
          'index_number, biomedical, chemical, civil, computer, electrical, electronic, material, mechanical, aeronautical, mechatronics, submitted_at'
        )
        .eq('index_number', indexNumber)
        .maybeSingle();

      if (error) throw error;
      return data as StudentPreferences | null;
    },

    async savePreferences(preferences: StudentPreferences): Promise<void> {
      const { error } = await client
        .from('student_preferences')
        .upsert(preferences, { onConflict: 'index_number' });

      if (error) throw error;
    }
  };
}

export const studentRepository = createStudentRepository(supabase);
