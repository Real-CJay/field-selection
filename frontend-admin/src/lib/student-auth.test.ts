import { describe, expect, it, vi } from 'vitest';
import { authenticateStudent, normalizeIndexNumber } from './student-auth';
import type { Student } from './types';

const student: Student = {
  index_number: '220001A',
  name: 'Test Student',
  email: 'test@example.test'
};

describe('student login', () => {
  it('normalizes an index number', () => {
    expect(normalizeIndexNumber(' 220001a ')).toBe('220001A');
  });

  it('accepts the shared password for an existing student', async () => {
    const findStudent = vi.fn().mockResolvedValue(student);
    const result = await authenticateStudent('220001a', 'student123', findStudent);
    expect(result).toEqual({ ok: true, student });
    expect(findStudent).toHaveBeenCalledWith('220001A');
  });

  it('rejects an incorrect password without querying Supabase', async () => {
    const findStudent = vi.fn();
    const result = await authenticateStudent('220001A', 'wrong', findStudent);
    expect(result).toEqual({ ok: false, message: 'Incorrect password.' });
    expect(findStudent).not.toHaveBeenCalled();
  });

  it('rejects an unknown index number', async () => {
    const result = await authenticateStudent(
      '999999Z',
      'student123',
      vi.fn().mockResolvedValue(null)
    );
    expect(result).toEqual({ ok: false, message: 'Student index number was not found.' });
  });

  it('returns a useful message when lookup fails', async () => {
    const result = await authenticateStudent(
      '220001A',
      'student123',
      vi.fn().mockRejectedValue(new Error('network'))
    );
    expect(result).toEqual({
      ok: false,
      message: 'Unable to check the student record. Please try again.'
    });
  });
});
