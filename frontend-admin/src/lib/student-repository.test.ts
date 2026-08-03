import { describe, expect, it, vi } from 'vitest';
import { createStudentRepository } from './student-repository';

describe('student repository', () => {
  it('loads student identity and read-only records through the backend loader', async () => {
    const recordLoader = vi.fn().mockResolvedValue({
      index_number: '220001A',
      name: 'Test Student',
      results: { average_gpa: 3.5 },
      preferences: { index_number: '220001A', computer: 1 }
    });
    const repository = createStudentRepository(recordLoader);

    await expect(repository.findStudent('220001A')).resolves.toEqual({
      index_number: '220001A',
      name: 'Test Student'
    });
    await expect(repository.getResults('220001A')).resolves.toMatchObject({ average_gpa: 3.5 });
    await expect(repository.getPreferences('220001A')).resolves.toMatchObject({ computer: 1 });
    expect(recordLoader).toHaveBeenCalledTimes(3);
  });

  it('does not expose student write methods', () => {
    const repository = createStudentRepository(vi.fn());
    expect(repository).not.toHaveProperty('savePreferences');
    expect(repository).not.toHaveProperty('saveGrades');
  });
});
