import { describe, expect, it, vi } from 'vitest';
import {
  ALLOCATION_DISCLAIMER,
  ALLOCATION_LOADING_DESCRIPTION,
  ALLOCATION_LOADING_TITLE,
  AllocationRequestError,
  createAllocationClient,
  formatCutoff,
  getAllocationErrorState,
  getDepartmentName,
  parseAllocationResult
} from './allocation';

const responseBody = {
  status: 'success',
  index_number: '250001E',
  name: 'Test Student',
  assigned_department: 'computer',
  average_gpa: 3.82,
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
  }
} as const;

describe('allocation results', () => {
  it('maps the confirmed successful response', () => {
    expect(parseAllocationResult(responseBody)).toEqual(responseBody);
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

  it('shows an unfilled cutoff as Open without rounding numeric values', () => {
    expect(formatCutoff(null)).toBe('Open');
    expect(formatCutoff(3.815)).toBe('3.815');
  });

  it('provides the required loading and disclaimer copy', () => {
    expect(ALLOCATION_LOADING_TITLE).toBe(
      'Waking up the server and calculating estimates...'
    );
    expect(ALLOCATION_LOADING_DESCRIPTION).toContain('50–60 seconds');
    expect(ALLOCATION_DISCLAIMER).toBe(
      'These cut-offs and placements are live estimates based on current student submissions. These are NOT final university results and your placement will fluctuate as more students enter their data.'
    );
  });

  it('selects the 404 state separately from the general error state', () => {
    expect(
      getAllocationErrorState(new AllocationRequestError('not-found', 'Not found', 404))
    ).toBe('not-found');
    expect(getAllocationErrorState(new Error('offline'))).toBe('error');
  });
});

describe('allocation client', () => {
  it('uses the caller-provided request without assuming a backend origin or authentication', async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify(responseBody), {
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        })
      );
    const client = createAllocationClient({
      fetcher,
      requestForIndex: (indexNumber) => ({
        input: `https://provided-by-integrator.test/api/allocation/${indexNumber}`,
        init: { headers: { Authorization: 'provided-by-integrator' } }
      })
    });

    await expect(client.getAllocation('250001E')).resolves.toEqual(responseBody);
    expect(fetcher).toHaveBeenCalledWith(
      'https://provided-by-integrator.test/api/allocation/250001E',
      {
        headers: { Authorization: 'provided-by-integrator' },
        method: 'GET'
      }
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

  it('reports an invalid JSON response separately', async () => {
    const client = createAllocationClient({
      fetcher: vi.fn().mockResolvedValue(new Response('not json', { status: 200 })),
      requestForIndex: () => ({ input: 'https://provided-by-integrator.test/result' })
    });

    await expect(client.getAllocation('250001E')).rejects.toMatchObject({
      kind: 'invalid-response'
    });
  });
});
