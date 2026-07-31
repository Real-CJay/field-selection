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

export type DepartmentCutoffs = Record<DepartmentId, number | null>;

export interface AllocationResult {
  status: 'success';
  index_number: string;
  name: string;
  assigned_department: DepartmentId | null;
  average_gpa: number;
  student_rank: number;
  cutoffs: DepartmentCutoffs;
  total_students_processed: number;
  accuracy_percentage: number;
}

export type CorrectableModule = 'cse' | 'maths' | 'electrical' | 'material';

export interface GradeCorrectionRequest {
  id: number;
  index_number: string;
  module: CorrectableModule;
  current_grade: number | null;
  requested_grade: ModuleGrade;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  reviewed_at: string | null;
}
