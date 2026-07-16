import { addApiLog } from '$lib/stores';
import { ApiError, type AllocationRun, type FieldSelectionApi, type ImportReport, type ImportType, type ResultQuery } from '$lib/types';
import { allocations, dashboard, fields } from './mock-data';

const configuredDelay = Number(import.meta.env.PUBLIC_MOCK_DELAY_MS ?? 650);
let lastRun: AllocationRun = { runId: 'mock-run-previous', status: 'completed', assigned: 573, unassigned: 3, completedAt: new Date().toISOString() };

async function request<T>(method: string, path: string, payload: unknown, response: () => T | Promise<T>): Promise<T> {
  const started = performance.now();
  await new Promise((resolve) => setTimeout(resolve, Math.max(120, configuredDelay)));
  try {
    const value = await response();
    addApiLog({ id: crypto.randomUUID(), timestamp: new Date().toISOString(), method, path, status: 200, duration: Math.round(performance.now() - started), request: payload, response: value });
    return value;
  } catch (error) {
    const apiError = error instanceof ApiError ? error : new ApiError({ status: 500, code: 'MOCK_ERROR', message: 'The mock service could not complete the request.' });
    addApiLog({ id: crypto.randomUUID(), timestamp: new Date().toISOString(), method, path, status: apiError.status, duration: Math.round(performance.now() - started), request: payload, response: { code: apiError.code, message: apiError.message } });
    throw apiError;
  }
}

function parseCsv(text: string) {
  return text.trim().split(/\r?\n/).filter(Boolean).map((line) => line.split(',').map((cell) => cell.trim()));
}

export const mockApi: FieldSelectionApi = {
  login(email, password) {
    return request('POST', '/auth/login', { email, password: '••••••••' }, () => {
      if (email.toLowerCase() !== 'admin@fieldselect.test' || password !== 'admin123') {
        throw new ApiError({ status: 401, code: 'INVALID_CREDENTIALS', message: 'Email or password is incorrect.' });
      }
      return { token: `mock-${crypto.randomUUID()}`, admin: { name: 'System Administrator', email } };
    });
  },
  getDashboard: () => request('GET', '/admin/dashboard', undefined, () => structuredClone(dashboard)),
  getFieldCapacities: () => request('GET', '/fields/capacities', undefined, () => structuredClone(fields)),
  async validateImport(type: ImportType, file: File, mapping: Record<string, string>) {
    return request('POST', `/imports/${type}/validate`, { fileName: file.name, mapping }, async () => {
      if (!file.name.toLowerCase().endsWith('.csv')) throw new ApiError({ status: 415, code: 'UNSUPPORTED_FILE', message: 'Only CSV files are supported.' });
      if (file.size > 5 * 1024 * 1024) throw new ApiError({ status: 413, code: 'FILE_TOO_LARGE', message: 'The file must be smaller than 5 MB.' });
      const rows = parseCsv(await file.text());
      if (rows.length < 2) throw new ApiError({ status: 422, code: 'EMPTY_FILE', message: 'The CSV must include a header and at least one data row.' });
      const headers = rows[0];
      const preview = rows.slice(1, 6).map((row) => Object.fromEntries(headers.map((header, i) => [header, row[i] ?? ''])));
      const issues = rows.slice(1).flatMap((row, i) => row.some((cell) => !cell) ? [{ row: i + 2, field: 'row', message: 'One or more required values are empty.' }] : []);
      const indexes = rows.slice(1).map((row) => row[0]);
      const duplicateRows = indexes.filter((value, i) => indexes.indexOf(value) !== i).length;
      return { type, fileName: file.name, totalRows: rows.length - 1, validRows: rows.length - 1 - issues.length - duplicateRows, invalidRows: issues.length, duplicateRows, issues, preview } satisfies ImportReport;
    });
  },
  uploadImport: (report) => request('POST', `/imports/${report.type}`, report, () => report),
  getReadiness: () => request('GET', '/allocations/readiness', undefined, () => [
    { label: 'Student records', detail: '576 records available', ready: true },
    { label: 'Academic results', detail: '572 of 576 records validated', ready: true },
    { label: 'Student preferences', detail: '568 submissions received', ready: true },
    { label: 'Validation issues', detail: '7 records need attention; run can continue', ready: false }
  ]),
  runAllocation: () => request('POST', '/allocations/run', undefined, async () => {
    lastRun = { runId: `mock-run-${Date.now()}`, status: 'processing', assigned: 0, unassigned: 0 };
    await new Promise((resolve) => setTimeout(resolve, 900));
    lastRun = { ...lastRun, status: 'completed', assigned: 573, unassigned: 3, completedAt: new Date().toISOString() };
    return lastRun;
  }),
  getAllocationStatus: () => request('GET', `/allocations/${lastRun.runId}`, undefined, () => lastRun),
  getResults(query: ResultQuery = {}) {
    return request('GET', '/allocations/results', query, () => allocations.filter((item) => {
      const search = query.search?.toLowerCase().trim();
      const matchesSearch = !search || item.student.indexNumber.toLowerCase().includes(search) || item.student.name.toLowerCase().includes(search);
      const matchesField = !query.field || query.field === 'all' || item.assignedField === query.field;
      const matchesStatus = !query.status || query.status === 'all' || item.status === query.status;
      return matchesSearch && matchesField && matchesStatus;
    }));
  }
};
