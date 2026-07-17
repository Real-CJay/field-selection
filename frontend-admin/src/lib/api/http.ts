import { addApiLog } from '$lib/stores';
import { ApiError, type FieldSelectionApi, type ImportReport, type ImportType, type ResultQuery } from '$lib/types';

const baseUrl = (import.meta.env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const started = performance.now();
  const isForm = body instanceof FormData;
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: isForm || body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : isForm ? body : JSON.stringify(body)
  });
  const value = await response.json().catch(() => ({}));
  addApiLog({ id: crypto.randomUUID(), timestamp: new Date().toISOString(), method, path, status: response.status, duration: Math.round(performance.now() - started), request: isForm ? '[FormData]' : body, response: value });
  if (!response.ok) throw new ApiError({ status: response.status, code: value.code ?? 'HTTP_ERROR', message: value.message ?? 'The backend request failed.', details: value });
  return value as T;
}

export const httpApi: FieldSelectionApi = {
  login: (email, password) => call('POST', '/auth/login', { email, password }),
  getDashboard: () => call('GET', '/admin/dashboard'),
  getFieldCapacities: () => call('GET', '/fields/capacities'),
  validateImport(type: ImportType, file: File, mapping: Record<string, string>) {
    const form = new FormData(); form.set('file', file); form.set('mapping', JSON.stringify(mapping));
    return call('POST', `/imports/${type}/validate`, form);
  },
  uploadImport: (report: ImportReport) => call('POST', `/imports/${report.type}`, report),
  getReadiness: () => call('GET', '/allocations/readiness'),
  runAllocation: () => call('POST', '/allocations/run'),
  getAllocationStatus: () => call('GET', '/allocations/status'),
  getResults: (query: ResultQuery = {}) => call('GET', `/allocations/results?${new URLSearchParams(Object.entries(query).filter(([, value]) => value) as [string, string][]).toString()}`)
};
