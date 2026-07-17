import { describe, expect, it } from 'vitest';
import { mockApi } from './mock';

describe('mock field-selection API', () => {
  it('accepts the documented demo credentials', async () => {
    const response = await mockApi.login('admin@fieldselect.test', 'admin123');
    expect(response.admin.email).toBe('admin@fieldselect.test');
    expect(response.token).toMatch(/^mock-/);
  });

  it('rejects invalid credentials with a typed API error', async () => {
    await expect(mockApi.login('wrong@example.test', 'incorrect')).rejects.toMatchObject({
      status: 401,
      code: 'INVALID_CREDENTIALS'
    });
  });

  it('returns a populated fictional dashboard', async () => {
    const dashboard = await mockApi.getDashboard();
    expect(dashboard.students).toBeGreaterThan(0);
    expect(dashboard.validationProblems).toBeGreaterThanOrEqual(0);
    expect(dashboard.recentOperations.length).toBeGreaterThan(0);
  });

  it('validates a CSV without persisting it', async () => {
    const file = new File(['Index Number,Name,Email\nMOCK240900,Test Student,test@example.test'], 'students.csv', { type: 'text/csv' });
    const report = await mockApi.validateImport('students', file, { 'Index Number': '0', Name: '1', Email: '2' });
    expect(report).toMatchObject({ totalRows: 1, validRows: 1, invalidRows: 0 });
  });

  it('filters results through the API interface', async () => {
    const results = await mockApi.getResults({ status: 'unassigned' });
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((result) => result.status === 'unassigned')).toBe(true);
  });
});
