import { DEPARTMENTS } from './preferences';
import type { AllocationResult, DepartmentCutoffs, DepartmentId } from './types';

export const ALLOCATION_LOADING_TITLE = 'Waking up the server and calculating estimates...';
export const ALLOCATION_LOADING_DESCRIPTION =
  'The first request can take 50–60 seconds while the server starts. Please keep this page open.';
export const ALLOCATION_DISCLAIMER =
  'These cut-offs and placements are live estimates based on current student submissions. These are NOT final university results and your placement will fluctuate as more students enter their data.';

export type AllocationErrorKind = 'not-found' | 'http' | 'network' | 'invalid-response';
export type AllocationErrorState = 'not-found' | 'error';
export type ConfidenceLevel = 'very-low' | 'low' | 'medium' | 'average' | 'high';

export interface Confidence {
  level: ConfidenceLevel;
  label: 'Very Low' | 'Low' | 'Medium' | 'Average' | 'High';
}

export class AllocationRequestError extends Error {
  constructor(
    public readonly kind: AllocationErrorKind,
    message: string,
    public readonly status?: number,
    options?: ErrorOptions
  ) {
    super(message, options);
    this.name = 'AllocationRequestError';
  }
}

export interface AllocationRequest {
  input: RequestInfo | URL;
  init?: RequestInit;
}

export interface AllocationClientConfig {
  fetcher: typeof fetch;
  requestForIndex: (indexNumber: string) => AllocationRequest;
}

const departmentIds = new Set<DepartmentId>(DEPARTMENTS.map(({ id }) => id));

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isDepartmentId(value: unknown): value is DepartmentId {
  return typeof value === 'string' && departmentIds.has(value as DepartmentId);
}

function readCutoffs(value: unknown): DepartmentCutoffs {
  if (!isRecord(value)) {
    throw new AllocationRequestError('invalid-response', 'Allocation cutoffs are missing.');
  }

  const entries = DEPARTMENTS.map(({ id }) => {
    const cutoff = value[id];
    if (cutoff !== null && (typeof cutoff !== 'number' || !Number.isFinite(cutoff))) {
      throw new AllocationRequestError(
        'invalid-response',
        `Allocation cutoff for ${id} is invalid.`
      );
    }
    return [id, cutoff] as const;
  });

  return Object.fromEntries(entries) as DepartmentCutoffs;
}

export function parseAllocationResult(value: unknown): AllocationResult {
  if (!isRecord(value) || value.status !== 'success') {
    throw new AllocationRequestError('invalid-response', 'Allocation response is invalid.');
  }
  if (typeof value.index_number !== 'string' || typeof value.name !== 'string') {
    throw new AllocationRequestError(
      'invalid-response',
      'Allocation student details are invalid.'
    );
  }
  if (value.assigned_department !== null && !isDepartmentId(value.assigned_department)) {
    throw new AllocationRequestError(
      'invalid-response',
      'Assigned allocation department is invalid.'
    );
  }
  if (typeof value.average_gpa !== 'number' || !Number.isFinite(value.average_gpa)) {
    throw new AllocationRequestError('invalid-response', 'Average GPA is invalid.');
  }
  if (!Number.isInteger(value.student_rank) || (value.student_rank as number) < 1) {
    throw new AllocationRequestError('invalid-response', 'Student rank is invalid.');
  }
  if (
    !Number.isInteger(value.total_students_processed) ||
    (value.total_students_processed as number) < 0
  ) {
    throw new AllocationRequestError('invalid-response', 'Processed student count is invalid.');
  }
  if (
    typeof value.accuracy_percentage !== 'number' ||
    !Number.isFinite(value.accuracy_percentage) ||
    value.accuracy_percentage < 0 ||
    value.accuracy_percentage > 100
  ) {
    throw new AllocationRequestError('invalid-response', 'Accuracy percentage is invalid.');
  }

  return {
    status: 'success',
    index_number: value.index_number,
    name: value.name,
    assigned_department: value.assigned_department,
    average_gpa: value.average_gpa,
    student_rank: value.student_rank as number,
    cutoffs: readCutoffs(value.cutoffs),
    total_students_processed: value.total_students_processed as number,
    accuracy_percentage: value.accuracy_percentage
  };
}

export function createAllocationClient(config: AllocationClientConfig) {
  return {
    async getAllocation(indexNumber: string): Promise<AllocationResult> {
      const request = config.requestForIndex(indexNumber);

      try {
        const response = await config.fetcher(request.input, {
          ...request.init,
          method: 'GET'
        });

        if (!response.ok) {
          const kind = response.status === 404 ? 'not-found' : 'http';
          throw new AllocationRequestError(
            kind,
            kind === 'not-found'
              ? 'No allocation result was found.'
              : 'The allocation request failed.',
            response.status
          );
        }

        let body: unknown;
        try {
          body = await response.json();
        } catch (cause) {
          throw new AllocationRequestError(
            'invalid-response',
            'The allocation response is not valid JSON.',
            response.status,
            { cause }
          );
        }

        return parseAllocationResult(body);
      } catch (error) {
        if (error instanceof AllocationRequestError) throw error;
        throw new AllocationRequestError(
          'network',
          'The allocation request could not be completed.',
          undefined,
          { cause: error }
        );
      }
    }
  };
}

export function getDepartmentName(id: DepartmentId | null): string {
  if (id === null) return 'No placement available';
  return DEPARTMENTS.find((department) => department.id === id)?.name ?? id;
}

export function formatCutoff(cutoff: number | null): string {
  return cutoff === null ? 'Open' : cutoff.toFixed(4);
}

export function formatGpa(gpa: number): string {
  return gpa.toFixed(4);
}

export function getConfidence(accuracyPercentage: number): Confidence {
  if (accuracyPercentage < 60) return { level: 'very-low', label: 'Very Low' };
  if (accuracyPercentage < 70) return { level: 'low', label: 'Low' };
  if (accuracyPercentage < 80) return { level: 'medium', label: 'Medium' };
  if (accuracyPercentage < 90) return { level: 'average', label: 'Average' };
  return { level: 'high', label: 'High' };
}

export function getAllocationErrorState(error: unknown): AllocationErrorState {
  return error instanceof AllocationRequestError && error.kind === 'not-found'
    ? 'not-found'
    : 'error';
}
