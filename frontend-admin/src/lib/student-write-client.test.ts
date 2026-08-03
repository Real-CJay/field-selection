import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { saveStudentApiSession } from './student-api-session';
import { isStudentWriteAuthError, saveStudentPreferences } from './student-write-client';

function memoryStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() { return values.size; },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => [...values.keys()][index] ?? null,
    removeItem: (key) => { values.delete(key); },
    setItem: (key, value) => { values.set(key, value); }
  };
}

const rankings = {
  biomedical: 1,
  chemical: 2,
  civil: 3,
  computer: 4,
  electrical: 5,
  electronic: 6,
  mechanical: 7,
  material: 8,
  aeronautical: 9,
  mechatronics: 10
} as const;

describe('student write client', () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, 'sessionStorage', {
      configurable: true,
      value: memoryStorage()
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it('uses the editable bearer token and never sends an index number', async () => {
    saveStudentApiSession({ accessMode: 'editable', token: 'edit.student-token' });
    const fetcher = vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ preferences: rankings }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    ));
    vi.stubGlobal('fetch', fetcher);
    await saveStudentPreferences(rankings);
    const [, options] = fetcher.mock.calls[0];
    expect(options.headers.Authorization).toBe('Bearer edit.student-token');
    expect(JSON.parse(options.body)).toEqual(rankings);
    expect(options.body).not.toContain('index_number');
  });

  it('classifies expired editable tokens as authentication errors', async () => {
    saveStudentApiSession({ accessMode: 'editable', token: 'edit.expired-token' });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: 'Student authentication is required.' }),
      { status: 401, headers: { 'Content-Type': 'application/json' } }
    )));
    try {
      await saveStudentPreferences(rankings);
      throw new Error('Expected the request to fail.');
    } catch (error) {
      expect(isStudentWriteAuthError(error)).toBe(true);
    }
  });
});
