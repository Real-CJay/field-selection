import type { SupabaseClient } from '@supabase/supabase-js';
import { describe, expect, it, vi } from 'vitest';
import { createStudentRepository } from './student-repository';
import type { StudentPreferences } from './types';

describe('student repository', () => {
  it('looks up one student by index number', async () => {
    const maybeSingle = vi.fn().mockResolvedValue({
      data: { index_number: '220001A', name: 'Test Student', email: 'test@example.test' },
      error: null
    });
    const eq = vi.fn().mockReturnValue({ maybeSingle });
    const select = vi.fn().mockReturnValue({ eq });
    const from = vi.fn().mockReturnValue({ select });
    const repository = createStudentRepository({ from } as unknown as SupabaseClient);

    await expect(repository.findStudent('220001A')).resolves.toMatchObject({
      index_number: '220001A'
    });
    expect(from).toHaveBeenCalledWith('students');
    expect(eq).toHaveBeenCalledWith('index_number', '220001A');
  });

  it('passes preference data to Supabase upsert with index conflict handling', async () => {
    const upsert = vi.fn().mockResolvedValue({ error: null });
    const from = vi.fn().mockReturnValue({ upsert });
    const repository = createStudentRepository({ from } as unknown as SupabaseClient);
    const preferences: StudentPreferences = {
      index_number: '220001A', biomedical: 1, chemical: 2, civil: 3, computer: 4,
      electrical: 5, electronic: 6, material: 7, mechanical: 8,
      aeronautical: 9, mechatronics: 10
    };

    await repository.savePreferences(preferences);
    expect(from).toHaveBeenCalledWith('student_preferences');
    expect(upsert).toHaveBeenCalledWith(preferences, { onConflict: 'index_number' });
  });

  it('propagates Supabase errors', async () => {
    const databaseError = new Error('database unavailable');
    const upsert = vi.fn().mockResolvedValue({ error: databaseError });
    const repository = createStudentRepository({
      from: vi.fn().mockReturnValue({ upsert })
    } as unknown as SupabaseClient);

    await expect(repository.savePreferences({} as StudentPreferences)).rejects.toBe(databaseError);
  });

  it('saves both student-entered module grades together', async () => {
    const upsert = vi.fn().mockResolvedValue({ error: null });
    const from = vi.fn().mockReturnValue({ upsert });
    const repository = createStudentRepository({ from } as unknown as SupabaseClient);

    await repository.saveGrades('220001A', 3.7, 3.3);

    expect(from).toHaveBeenCalledWith('student_results');
    expect(upsert).toHaveBeenCalledWith(
      { index_number: '220001A', fluids: 3.7, mechanics: 3.3 },
      { onConflict: 'index_number' }
    );
  });
});
