import { describe, expect, it, vi } from 'vitest';
import { authenticateAdmin, getAdminDepartments, getAdminReport } from './admin-client';

describe('admin authentication client', () => {
  it('sends the CJay credentials to the protected backend login endpoint', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ username: 'CJay', admin_token: 'signed-token' }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    ));

    await expect(authenticateAdmin('CJay', 'admin-password', fetcher))
      .resolves.toEqual({ username: 'CJay', admin_token: 'signed-token' });

    expect(fetcher).toHaveBeenCalledOnce();
    const [url, options] = fetcher.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/admin\/login$/);
    expect(JSON.parse(options.body)).toEqual({
      username: 'CJay',
      password: 'admin-password'
    });
    expect(options.headers.Authorization).toBeUndefined();
  });

  it('returns the backend admin error without attempting student authentication', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Invalid administrator credentials.' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    ));

    await expect(authenticateAdmin('CJay', 'wrong-password', fetcher)).rejects.toThrow(
      'Invalid administrator credentials.'
    );
  });
});

describe('admin reporting client', () => {
  it('keeps department rows and the cohort summary together', async () => {
    const payload = {
      departments: [{ department: 'civil', quota: 125 }],
      summary: {
        total_students_processed: 700,
        total_cohort: 743,
        coverage_percentage: 94.2,
        coverage_band: 'High',
        total_capacity: 753,
        selected_min: 700,
        selected_max: 700,
        coverage_note: 'Cohort coverage is not prediction accuracy.'
      }
    };
    const fetcher = vi.fn().mockResolvedValue(new Response(
      JSON.stringify(payload),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    ));

    await expect(getAdminDepartments('admin-token', fetcher)).resolves.toEqual(payload);
    const [url, options] = fetcher.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/admin\/departments$/);
    expect(options.headers.Authorization).toBe('Bearer admin-token');
  });

  it('downloads the protected detailed CSV using the server filename', async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(
      'Department,Department rank\r\nCivil Engineering,1\r\n',
      {
        status: 200,
        headers: {
          'Content-Type': 'text/csv',
          'Content-Disposition': 'attachment; filename="field-selection-student-rankings-2026-08-03.csv"'
        }
      }
    ));

    const report = await getAdminReport('student-rankings', 'admin-token', fetcher);
    expect(report.filename).toBe('field-selection-student-rankings-2026-08-03.csv');
    await expect(report.blob.text()).resolves.toContain('Civil Engineering,1');
    const [url, options] = fetcher.mock.calls[0];
    expect(String(url)).toMatch(/\/api\/admin\/reports\/student-rankings\.csv$/);
    expect(options.headers.Authorization).toBe('Bearer admin-token');
  });
});
