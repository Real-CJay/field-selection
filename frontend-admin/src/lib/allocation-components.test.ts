import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import AllocationLoading from './components/AllocationLoading.svelte';
import AllocationResults from './components/AllocationResults.svelte';
import AllocationStatus from './components/AllocationStatus.svelte';
import type { AllocationResult } from './types';

const result: AllocationResult = {
  status: 'success',
  index_number: '250001E',
  name: 'Test Student',
  assigned_department: 'computer',
  average_gpa: 3.8214,
  allocation_gpa: 3.82,
  student_rank: 12,
  allocation_status: 'certain',
  possible_departments: ['computer'],
  border_departments: [],
  guaranteed_department: 'computer',
  allocation_explanation: null,
  cutoffs: {
    biomedical: { status: 'fixed', value: 3.42, incomplete: false },
    chemical: { status: 'fixed', value: 3.15, incomplete: false },
    civil: { status: 'open', incomplete: false },
    computer: { status: 'fixed', value: 3.81, incomplete: false },
    electrical: { status: 'fixed', value: 3.5, incomplete: false },
    electronic: { status: 'fixed', value: 3.55, incomplete: false },
    material: { status: 'fixed', value: 3.1, incomplete: false },
    mechanical: { status: 'fixed', value: 3.25, incomplete: false },
    aeronautical: { status: 'open', incomplete: false },
    mechatronics: { status: 'fixed', value: 3.6, incomplete: false }
  },
  total_students_processed: 45,
  accuracy_percentage: 6.1
};

describe('allocation components', () => {
  it('renders identity, department, four-decimal GPA, rank, accuracy, confidence, and disclaimer', () => {
    const { body } = render(AllocationResults, { props: { result } });

    expect(body).toContain('Test Student');
    expect(body).toContain('250001E');
    expect(body).toContain('Computer Science and Engineering');
    expect(body).toContain('3.8214');
    expect(body).toContain('#12');
    expect(body).toContain('6.1%');
    expect(body).toContain('Very Low');
    expect(body).toContain('Open');
    expect(body).toContain('These are NOT final university results');
    expect(body).toContain('encourage other students');
    expect(body.indexOf('Important:')).toBeLessThan(body.indexOf('Current estimated cut-offs'));
    expect(body).toContain('What is confidence?');
    expect(body).toContain('0–&lt;60%:');
    expect(body).toContain('90–100%:');
    expect(body).toContain('View GPA distribution');
  });

  it('renders border departments and the guaranteed fallback', () => {
    const borderResult: AllocationResult = {
      ...result,
      assigned_department: null,
      allocation_status: 'border',
      possible_departments: ['computer', 'electrical', 'mechanical'],
      border_departments: ['computer', 'electrical'],
      guaranteed_department: 'mechanical',
      allocation_explanation: 'Subject marks are needed to resolve the higher choices.'
    };
    const { body } = render(AllocationResults, { props: { result: borderResult } });
    expect(body).toContain('Placement is on a border');
    expect(body).toContain('Computer Science and Engineering, Electrical Engineering');
    expect(body).toContain('guaranteed Mechanical Engineering or a higher-ranked');
  });

  it('renders the Render cold-start loading state', () => {
    const { body } = render(AllocationLoading);
    expect(body).toContain('Waking up the server and calculating estimates...');
    expect(body).toContain('50–60 seconds');
  });

  it('renders distinct not-found and general-error states', () => {
    expect(render(AllocationStatus, { props: { state: 'not-found' } }).body).toContain(
      'No allocation result found'
    );
    expect(render(AllocationStatus, { props: { state: 'error' } }).body).toContain(
      'Unable to load allocation results'
    );
  });
});
