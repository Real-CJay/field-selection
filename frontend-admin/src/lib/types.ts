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
  assigned_department: DepartmentId;
  average_gpa: number;
  cutoffs: DepartmentCutoffs;
}
