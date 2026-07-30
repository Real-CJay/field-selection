import { describe, expect, it, vi } from 'vitest';
import {
  ALLOCATION_DISCLAIMER,
  ALLOCATION_LOADING_DESCRIPTION,
  ALLOCATION_LOADING_TITLE,
  AllocationRequestError,
  createAllocationClient,
  formatCutoff,
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
  student_rank: 12,
  cutoffs: {
    biomedical: 3.42,
    chemical: 3.15,
    civil: null,
    computer: 3.81,
    electrical: 3.5,
    electronic: 3.55,
    material: 3.1,
    mechanical: 3.25,
    aeronautical: null,
    mechatronics: 3.6
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

  it('formats GPA and cutoffs at four decimal places', () => {
    expect(formatCutoff(null)).toBe('Open');
    expect(formatCutoff(3.815)).toBe('3.8150');
    expect(formatGpa(3.82)).toBe('3.8200');
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
