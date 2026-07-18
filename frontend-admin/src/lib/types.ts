export interface Student {
  index_number: string;
  name: string;
  email: string;
}

export interface StudentSession {
  indexNumber: string;
  name: string;
}

export type DepartmentId =
  | 'biomedical'
  | 'chemical'
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
  computer: number;
  electrical: number;
  electronic: number;
  material: number;
  mechanical: number;
  aeronautical: number;
  mechatronics: number;
  submitted_at?: string;
}
