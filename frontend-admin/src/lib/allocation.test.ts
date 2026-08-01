import { describe, expect, it, vi } from 'vitest';
import {
  ALLOCATION_DISCLAIMER,
  ALLOCATION_LOADING_DESCRIPTION,
  ALLOCATION_LOADING_TITLE,
  AllocationRequestError,
  createAllocationClient,
  formatCutoff,
  departmentsByDescendingCutoff,
  formatGpa,
  getAllocationErrorState,
  getConfidence,
  getDepartmentName,
  parseAllocationResult
} from './allocation';

const responseBody = {
  status: 'success',
  index_number: '250001E',
  name: 'Test Student',
  assigned_department: 'computer',
  average_gpa: 3.8214,
  allocation_gpa: 3.82,
  student_rank: 12,
  allocation_status: 'certain',
  possible_departments: ['computer'],
  border_departments: [],
  guaranteed_department: 'computer',
  allocation_explanation: null,
  cutoffs: {
    biomedical: { status: 'fixed', value: 3.42, incomplete: false },
    chemical: { status: 'fixed', value: 3.15, incomplete: false },
    civil: { status: 'open', incomplete: false },
    computer: { status: 'fixed', value: 3.81, incomplete: false },
    electrical: { status: 'fixed', value: 3.5, incomplete: false },
    electronic: { status: 'fixed', value: 3.55, incomplete: false },
    material: { status: 'fixed', value: 3.1, incomplete: false },
    mechanical: { status: 'fixed', value: 3.25, incomplete: false },
    aeronautical: { status: 'open', incomplete: false },
    mechatronics: { status: 'range', min: 3.57, max: 3.6, open_possible: false, incomplete: false }
  },
  total_students_processed: 45,
  accuracy_percentage: 6.1
} as const;

describe('allocation results', () => {
  it('maps the complete successful response', () => {
    expect(parseAllocationResult(responseBody)).toEqual(responseBody);
  });

  it('accepts a nullable placement', () => {
    expect(parseAllocationResult({ ...responseBody, assigned_department: null })).toMatchObject({
      assigned_department: null
    });
    expect(getDepartmentName(null)).toBe('No placement available');
  });

  it('rejects a response that omits a department cutoff', () => {
    const invalid = {
      ...responseBody,
      cutoffs: { ...responseBody.cutoffs, biomedical: undefined }
    };
    expect(() => parseAllocationResult(invalid)).toThrow(AllocationRequestError);
  });

  it('uses the existing department labels', () => {
    expect(getDepartmentName('computer')).toBe('Computer Science and Engineering');
  });

  it('formats display GPA at four decimals and allocation cutoffs at two decimals', () => {
    expect(formatCutoff({ status: 'open', incomplete: false })).toBe('Open');
    expect(formatCutoff({ status: 'fixed', value: 3.815, incomplete: false })).toBe('3.81');
    expect(formatCutoff({
      status: 'range', min: 3.57, max: 3.6, open_possible: false, incomplete: false
    })).toBe('3.57–3.60');
    expect(formatGpa(3.82)).toBe('3.8200');
  });

  it('sorts cutoff departments descending and keeps open quotas last', () => {
    const sorted = departmentsByDescendingCutoff(responseBody.cutoffs);
    expect(sorted.map(({ id }) => id)).toEqual([
      'computer', 'mechatronics', 'electronic', 'electrical', 'biomedical',
      'mechanical', 'chemical', 'material', 'civil', 'aeronautical'
    ]);
  });

  it('maps every confidence boundary', () => {
    expect(getConfidence(0).label).toBe('Very Low');
    expect(getConfidence(59.9).label).toBe('Very Low');
    expect(getConfidence(60).label).toBe('Low');
    expect(getConfidence(70).label).toBe('Medium');
    expect(getConfidence(80).label).toBe('Average');
    expect(getConfidence(90).label).toBe('High');
    expect(getConfidence(100).label).toBe('High');
  });

  it('provides the required loading and disclaimer copy', () => {
    expect(ALLOCATION_LOADING_TITLE).toBe(
      'Waking up the server and calculating estimates...'
    );
    expect(ALLOCATION_LOADING_DESCRIPTION).toContain('50–60 seconds');
    expect(ALLOCATION_DISCLAIMER).toContain('These are NOT final university results');
  });

  it('selects the 404 state separately from the general error state', () => {
    expect(
      getAllocationErrorState(new AllocationRequestError('not-found', 'Not found', 404))
    ).toBe('not-found');
    expect(getAllocationErrorState(new Error('offline'))).toBe('error');
  });
});

describe('allocation client', () => {
  it('uses the caller-provided request', async () => {
    const fetcher = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responseBody), {
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      })
    );
    const client = createAllocationClient({
      fetcher,
      requestForIndex: (indexNumber) => ({
        input: `https://provided-by-integrator.test/api/allocation/${indexNumber}`
      })
    });

    await expect(client.getAllocation('250001E')).resolves.toEqual(responseBody);
    expect(fetcher).toHaveBeenCalledWith(
      'https://provided-by-integrator.test/api/allocation/250001E',
      { method: 'GET' }
    );
  });

  it('reports an HTTP 404 as not found', async () => {
    const client = createAllocationClient({
      fetcher: vi.fn().mockResolvedValue(new Response(null, { status: 404 })),
      requestForIndex: () => ({ input: 'https://provided-by-integrator.test/result' })
    });

    await expect(client.getAllocation('250001E')).rejects.toMatchObject({
      kind: 'not-found',
      status: 404
    });
  });

  it('reports invalid JSON separately', async () => {
    const client = createAllocationClient({
      fetcher: vi.fn().mockResolvedValue(new Response('not json', { status: 200 })),
      requestForIndex: () => ({ input: 'https://provided-by-integrator.test/result' })
    });

    await expect(client.getAllocation('250001E')).rejects.toMatchObject({
      kind: 'invalid-response'
    });
  });
});
