import { DEPARTMENTS } from './preferences';
import type {
  AllocationResult,
  CutoffEstimate,
  DepartmentCutoffs,
  DepartmentId
} from './types';

export const ALLOCATION_LOADING_TITLE = 'Waking up the server and calculating estimates...';
export const ALLOCATION_LOADING_DESCRIPTION =
  'The first request can take 50–60 seconds while the server starts. Please keep this page open.';
export const ALLOCATION_DISCLAIMER =
  'These cut-offs and placements are live estimates based on current student submissions. These are NOT final university results and your placement will fluctuate as more students enter their data. Please encourage other students to complete the module grades and field preference form so these estimates become more reliable.';

export type AllocationErrorKind = 'not-found' | 'http' | 'network' | 'invalid-response';
export type AllocationErrorState = 'not-found' | 'error';
export type ConfidenceLevel = 'very-low' | 'low' | 'medium' | 'average' | 'high' | 'very-high';

export interface Confidence {
  level: ConfidenceLevel;
  label: 'Very Low' | 'Low' | 'Medium' | 'Average' | 'High' | 'Very High';
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

function readCutoff(value: unknown, department: DepartmentId): CutoffEstimate {
  if (!isRecord(value) || typeof value.status !== 'string' || typeof value.incomplete !== 'boolean') {
    throw new AllocationRequestError('invalid-response', `Allocation cutoff for ${department} is invalid.`);
  }
  if (value.status === 'open') return { status: 'open', incomplete: value.incomplete };
  if (value.status === 'fixed' && typeof value.value === 'number' && Number.isFinite(value.value)) {
    return { status: 'fixed', value: value.value, incomplete: value.incomplete };
  }
  if (
    value.status === 'range' &&
    typeof value.min === 'number' && Number.isFinite(value.min) &&
    typeof value.max === 'number' && Number.isFinite(value.max) &&
    typeof value.open_possible === 'boolean'
  ) {
    return {
      status: 'range', min: value.min, max: value.max,
      open_possible: value.open_possible, incomplete: value.incomplete
    };
  }
  throw new AllocationRequestError('invalid-response', `Allocation cutoff for ${department} is invalid.`);
}

function readCutoffs(value: unknown): DepartmentCutoffs {
  if (!isRecord(value)) {
    throw new AllocationRequestError('invalid-response', 'Allocation cutoffs are missing.');
  }

  const entries = DEPARTMENTS.map(({ id }) => {
    return [id, readCutoff(value[id], id)] as const;
  });

  return Object.fromEntries(entries) as DepartmentCutoffs;
}

function readDepartments(value: unknown, label: string): DepartmentId[] {
  if (!Array.isArray(value) || value.some((item) => !isDepartmentId(item))) {
    throw new AllocationRequestError('invalid-response', `${label} are invalid.`);
  }
  return value as DepartmentId[];
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
  if (typeof value.allocation_gpa !== 'number' || !Number.isFinite(value.allocation_gpa)) {
    throw new AllocationRequestError('invalid-response', 'Allocation GPA is invalid.');
  }
  if (!['certain', 'border', 'unresolved'].includes(value.allocation_status as string)) {
    throw new AllocationRequestError('invalid-response', 'Allocation status is invalid.');
  }
  if (value.guaranteed_department !== null && !isDepartmentId(value.guaranteed_department)) {
    throw new AllocationRequestError('invalid-response', 'Guaranteed department is invalid.');
  }
  if (value.allocation_explanation !== null && typeof value.allocation_explanation !== 'string') {
    throw new AllocationRequestError('invalid-response', 'Allocation explanation is invalid.');
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
    allocation_gpa: value.allocation_gpa,
    student_rank: value.student_rank as number,
    allocation_status: value.allocation_status as AllocationResult['allocation_status'],
    possible_departments: readDepartments(value.possible_departments, 'Possible departments'),
    border_departments: readDepartments(value.border_departments, 'Border departments'),
    guaranteed_department: value.guaranteed_department,
    allocation_explanation: value.allocation_explanation,
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

export function formatCutoff(cutoff: CutoffEstimate): string {
  if (cutoff.status === 'open') return 'Open';
  if (cutoff.status === 'fixed') return cutoff.value.toFixed(2);
  const range = cutoff.min === cutoff.max
    ? cutoff.min.toFixed(2)
    : `${cutoff.min.toFixed(2)}–${cutoff.max.toFixed(2)}`;
  return cutoff.open_possible ? `Open or ${range}` : range;
}

export function departmentsByDescendingCutoff(cutoffs: DepartmentCutoffs) {
  const cutoffValue = (cutoff: CutoffEstimate): number => {
    if (cutoff.status === 'open') return Number.NEGATIVE_INFINITY;
    return cutoff.status === 'fixed' ? cutoff.value : cutoff.max;
  };
  return [...DEPARTMENTS].sort((left, right) =>
    cutoffValue(cutoffs[right.id]) - cutoffValue(cutoffs[left.id])
  );
}

export function formatGpa(gpa: number): string {
  return gpa.toFixed(4);
}

export function getConfidence(accuracyPercentage: number): Confidence {
  if (accuracyPercentage < 60) return { level: 'very-low', label: 'Very Low' };
  if (accuracyPercentage < 70) return { level: 'low', label: 'Low' };
  if (accuracyPercentage < 80) return { level: 'medium', label: 'Medium' };
  if (accuracyPercentage < 90) return { level: 'average', label: 'Average' };
  if (accuracyPercentage < 95) return { level: 'high', label: 'High' };
  return { level: 'very-high', label: 'Very High' };
}

export function getAllocationErrorState(error: unknown): AllocationErrorState {
  return error instanceof AllocationRequestError && error.kind === 'not-found'
    ? 'not-found'
    : 'error';
}
