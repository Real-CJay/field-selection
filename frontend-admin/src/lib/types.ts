export type ImportType = 'students' | 'results' | 'preferences';
export type AllocationStatus = 'assigned' | 'unassigned';

export interface Student {
  id: string;
  indexNumber: string;
  name: string;
  email: string;
}

export interface AcademicResult {
  studentId: string;
  sgpa: number;
  grades: Record<string, string>;
}

export interface Preference {
  studentId: string;
  rankedFieldIds: string[];
  submittedAt: string;
}

export interface FieldCapacity {
  id: string;
  name: string;
  shortName: string;
  capacity: number;
  assigned: number;
}

export interface Allocation {
  id: string;
  student: Student;
  sgpa: number;
  assignedField: string | null;
  preferenceRank: number | null;
  status: AllocationStatus;
  reason?: string;
  grades: Record<string, string>;
  preferences: string[];
}

export interface ImportIssue {
  row: number;
  field: string;
  message: string;
}

export interface ImportReport {
  type: ImportType;
  fileName: string;
  totalRows: number;
  validRows: number;
  invalidRows: number;
  duplicateRows: number;
  issues: ImportIssue[];
  preview: Record<string, string>[];
}

export interface DashboardSummary {
  students: number;
  results: number;
  preferences: number;
  allocations: number;
  validationProblems: number;
  recentOperations: Operation[];
}

export interface Operation {
  id: string;
  label: string;
  detail: string;
  status: 'success' | 'warning' | 'error';
  occurredAt: string;
}

export interface ReadinessCheck {
  label: string;
  detail: string;
  ready: boolean;
}

export interface AllocationRun {
  runId: string;
  status: 'idle' | 'processing' | 'completed' | 'failed';
  assigned: number;
  unassigned: number;
  completedAt?: string;
}

export interface ApiErrorShape {
  status: number;
  code: string;
  message: string;
  details?: unknown;
}

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(error: ApiErrorShape) {
    super(error.message);
    this.name = 'ApiError';
    this.status = error.status;
    this.code = error.code;
    this.details = error.details;
  }
}

export interface LoginResponse {
  token: string;
  admin: { name: string; email: string };
}

export interface ResultQuery {
  search?: string;
  field?: string;
  status?: 'all' | AllocationStatus;
}

export interface FieldSelectionApi {
  login(email: string, password: string): Promise<LoginResponse>;
  getDashboard(): Promise<DashboardSummary>;
  getFieldCapacities(): Promise<FieldCapacity[]>;
  validateImport(type: ImportType, file: File, mapping: Record<string, string>): Promise<ImportReport>;
  uploadImport(report: ImportReport): Promise<ImportReport>;
  getReadiness(): Promise<ReadinessCheck[]>;
  runAllocation(): Promise<AllocationRun>;
  getAllocationStatus(): Promise<AllocationRun>;
  getResults(query?: ResultQuery): Promise<Allocation[]>;
}

export interface ApiLogEntry {
  id: string;
  timestamp: string;
  method: string;
  path: string;
  status: number;
  duration: number;
  request?: unknown;
  response?: unknown;
}
