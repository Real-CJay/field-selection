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
  student_rank: 12,
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
