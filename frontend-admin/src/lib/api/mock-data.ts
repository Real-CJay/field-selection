import type { Allocation, DashboardSummary, FieldCapacity, Operation } from '$lib/types';

export const fields: FieldCapacity[] = [
  { id: 'computer', name: 'Computer Science & Engineering', shortName: 'CSE', capacity: 200, assigned: 188 },
  { id: 'electronic', name: 'Electronic & Telecommunication', shortName: 'ENTC', capacity: 100, assigned: 94 },
  { id: 'electrical', name: 'Electrical Engineering', shortName: 'EE', capacity: 90, assigned: 82 },
  { id: 'mechanical', name: 'Mechanical Engineering', shortName: 'ME', capacity: 80, assigned: 75 },
  { id: 'civil', name: 'Civil Engineering', shortName: 'CE', capacity: 115, assigned: 107 },
  { id: 'chemical', name: 'Chemical & Process Engineering', shortName: 'CPE', capacity: 78, assigned: 70 },
  { id: 'material', name: 'Materials Science & Engineering', shortName: 'MSE', capacity: 45, assigned: 39 },
  { id: 'biomedical', name: 'Biomedical Engineering', shortName: 'BME', capacity: 15, assigned: 14 },
  { id: 'aeronautical', name: 'Aeronautical Engineering', shortName: 'AE', capacity: 10, assigned: 9 },
  { id: 'mechatronics', name: 'Mechatronics Engineering', shortName: 'MTE', capacity: 10, assigned: 8 }
];

const firstNames = ['Ari', 'Nima', 'Kavi', 'Maya', 'Ravi', 'Tara', 'Ishan', 'Lena', 'Noah', 'Zara', 'Dilan', 'Amara'];
const lastNames = ['Perera', 'Silva', 'Fernando', 'Jayasekara', 'De Alwis', 'Wijesinghe'];
const grades = ['A+', 'A', 'A-', 'B+', 'B', 'B-'];

export const allocations: Allocation[] = Array.from({ length: 47 }, (_, index) => {
  const field = fields[index % fields.length];
  const unassigned = index === 13 || index === 31 || index === 44;
  const indexNumber = `MOCK${String(240001 + index)}`;
  return {
    id: `allocation-${index + 1}`,
    student: {
      id: `student-${index + 1}`,
      indexNumber,
      name: `${firstNames[index % firstNames.length]} ${lastNames[index % lastNames.length]}`,
      email: `student${index + 1}@example.test`
    },
    sgpa: Number((3.94 - index * 0.037).toFixed(2)),
    assignedField: unassigned ? null : field.id,
    preferenceRank: unassigned ? null : (index % 4) + 1,
    status: unassigned ? 'unassigned' : 'assigned',
    reason: unassigned ? (index === 13 ? 'Academic results are incomplete' : 'No preferred field has available capacity') : undefined,
    grades: { MA1010: grades[index % grades.length], CS1032: grades[(index + 1) % grades.length], EE1010: grades[(index + 2) % grades.length] },
    preferences: fields.slice(0, 5).map((item) => item.id)
  };
});

export const recentOperations: Operation[] = [
  { id: 'op-1', label: 'Results validation completed', detail: '572 valid rows, 4 require review', status: 'warning', occurredAt: '10 minutes ago' },
  { id: 'op-2', label: 'Student accounts imported', detail: '576 fictional test records accepted', status: 'success', occurredAt: 'Yesterday, 4:16 PM' },
  { id: 'op-3', label: 'Allocation simulation completed', detail: '573 assigned, 3 unassigned', status: 'success', occurredAt: 'Yesterday, 2:40 PM' },
  { id: 'op-4', label: 'Preferences upload rejected', detail: 'Duplicate index numbers detected', status: 'error', occurredAt: '12 Jul, 11:05 AM' }
];

export const dashboard: DashboardSummary = {
  students: 576,
  results: 572,
  preferences: 568,
  allocations: 573,
  validationProblems: 7,
  recentOperations
};
