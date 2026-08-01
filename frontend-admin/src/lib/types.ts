export interface Student {
  index_number: string;
  name: string;
  email: string;
}

export interface StudentSession {
  indexNumber: string;
  name: string;
}

export type ModuleGrade =
  | 'A+'
  | 'A'
  | 'A-'
  | 'B+'
  | 'B'
  | 'B-'
  | 'C+'
  | 'C'
  | 'C-'
  | 'D'
  | 'F';

export interface ModuleGrades {
  fluidMechanics: ModuleGrade;
  mechanics: ModuleGrade;
}

export interface StudentResults {
  index_number: string;
  average_gpa?: number;
  cse?: number;
  electrical?: number;
  fluids?: number;
  maths?: number;
  mechanics?: number;
  material?: number;
}

export type DepartmentId =
  | 'biomedical'
  | 'chemical'
  | 'civil'
  | 'computer'
  | 'electrical'
  | 'electronic'
  | 'material'
  | 'mechanical'
  | 'aeronautical'
  | 'mechatronics';

export type RankingValue = number | '';
export type StudentRankings = Record<DepartmentId, RankingValue>;

export interface StudentPreferences {
  index_number: string;
  biomedical: number;
  chemical: number;
  civil: number;
  computer: number;
  electrical: number;
  electronic: number;
  material: number;
  mechanical: number;
  aeronautical: number;
  mechatronics: number;
  submitted_at?: string;
}

export type CutoffEstimate =
  | { status: 'open'; incomplete: boolean }
  | { status: 'fixed'; value: number; incomplete: boolean }
  | {
      status: 'range';
      min: number;
      max: number;
      open_possible: boolean;
      incomplete: boolean;
    };

export type DepartmentCutoffs = Record<DepartmentId, CutoffEstimate>;

export interface AllocationResult {
  status: 'success';
  index_number: string;
  name: string;
  assigned_department: DepartmentId | null;
  average_gpa: number;
  allocation_gpa: number;
  student_rank: number;
  allocation_status: 'certain' | 'border' | 'unresolved';
  possible_departments: DepartmentId[];
  border_departments: DepartmentId[];
  guaranteed_department: DepartmentId | null;
  allocation_explanation: string | null;
  cutoffs: DepartmentCutoffs;
  total_students_processed: number;
  accuracy_percentage: number;
}

export type CorrectableModule = 'cse' | 'maths' | 'electrical' | 'material';

export interface GradeCorrectionRequest {
  id: number;
  index_number: string;
  module: CorrectableModule;
  current_grade: string;
  requested_grade: ModuleGrade;
  status: 'pending' | 'approved' | 'rejected' | 'superseded' | 'reverted';
  created_at: string;
  reviewed_at: string | null;
  reverted_at: string | null;
}

export interface DepartmentGpaGroup {
  gpa: number;
  min_count: number;
  max_count: number;
}

export interface GpaLookupAllocationGroup {
  allocation_status: 'certain' | 'border' | 'unresolved';
  assigned_department: DepartmentId | null;
  possible_departments: DepartmentId[];
  border_departments: DepartmentId[];
  guaranteed_department: DepartmentId | null;
  count: number;
}

export interface GpaLookupTiebreakGroup {
  department: DepartmentId;
  subjects: Array<{
    subject: 'cse' | 'maths' | 'electrical' | 'fluids' | 'mechanics' | 'material';
    grade: string;
    value: number;
  }>;
  score: number;
  candidate_count: number;
  score_tied: boolean;
  selection_status: 'selected' | 'border';
  count: number;
}

export interface GpaLookupResult {
  status: 'success';
  gpa: number;
  count: number;
  total_students_processed: number;
  allocation_groups: GpaLookupAllocationGroup[];
  tiebreak_groups: GpaLookupTiebreakGroup[];
}

export interface AdminStudentRecord {
  index_number: string;
  name: string;
  average_gpa: number | null;
  grades: Record<'cse' | 'maths' | 'electrical' | 'fluids' | 'mechanics' | 'material', string>;
  preferences: DepartmentId[];
  submitted_at: string | null;
  allocation: {
    allocation_status: 'certain' | 'border' | 'unresolved' | 'incomplete';
    assigned_department: DepartmentId | null;
    possible_departments: DepartmentId[];
    border_departments: DepartmentId[];
    guaranteed_department: DepartmentId | null;
  };
}

export interface AdminDepartmentTiebreaker {
  subjects: Array<{
    subject: keyof AdminStudentRecord['grades'];
    grade: string;
    value: number;
  }>;
  score: number;
  candidate_count: number;
  score_tied: boolean;
}

export interface AdminDepartmentStudent {
  index_number: string;
  name: string;
  average_gpa: number;
  allocation_gpa: number;
  selection_status: 'selected' | 'border';
  selected_state_count: number;
  total_states: number;
  tiebreaker: AdminDepartmentTiebreaker | null;
}

export interface AdminDepartmentRecord {
  department: DepartmentId;
  quota: number;
  selected_min: number;
  selected_max: number;
  cutoff: CutoffEstimate;
  incomplete: boolean;
  students: AdminDepartmentStudent[];
}
