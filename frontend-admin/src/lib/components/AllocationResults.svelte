<script lang="ts">
  import {
    ALLOCATION_DISCLAIMER,
    departmentsByDescendingCutoff,
    formatCutoff,
    formatGpa,
    getConfidence,
    getDepartmentName
  } from '$lib/allocation';
  import { getDepartmentGpas } from '$lib/department-client';
  import { getAnonymousGpaLookup } from '$lib/gpa-lookup-client';
  import { DEPARTMENTS } from '$lib/preferences';
  import type {
    AllocationResult,
    DepartmentGpaGroup,
    DepartmentId,
    GpaLookupAllocationGroup,
    GpaLookupResult
  } from '$lib/types';

  const subjectNames = {
    cse: 'CSE', maths: 'Mathematics', electrical: 'Electrical',
    fluids: 'Fluid Mechanics', mechanics: 'Mechanics', material: 'Material Science'
  } as const;

  let { result }: { result: AllocationResult } = $props();
  let confidence = $derived(getConfidence(result.accuracy_percentage));
  let sortedDepartments = $derived(departmentsByDescendingCutoff(result.cutoffs));
  let selectedDepartment = $state<DepartmentId | null>(null);
  let departmentGroups = $state<DepartmentGpaGroup[]>([]);
  let departmentLoading = $state(false);
  let departmentError = $state('');
  let departmentIncomplete = $state(false);
  let lookupValue = $state<string | null>(null);
  let lookupResult = $state<GpaLookupResult | null>(null);
  let lookupLoading = $state(false);
  let lookupError = $state('');

  function departmentList(departments: DepartmentId[]): string {
    return departments.map(getDepartmentName).join(', ');
  }

  function resultHeading(): string {
    if (result.assigned_department) return getDepartmentName(result.assigned_department);
    if (result.allocation_status === 'border') return 'Placement is on a border';
    return 'Placement is currently unresolved';
  }

  function lookupOutcome(group: GpaLookupAllocationGroup): string {
    if (group.assigned_department) {
      return getDepartmentName(group.assigned_department);
    }
    if (group.possible_departments.length) {
      const possible = departmentList(group.possible_departments);
      return group.guaranteed_department
        ? `${possible} · guaranteed ${getDepartmentName(group.guaranteed_department)} or higher`
        : possible;
    }
    return 'Placement currently unresolved';
  }

  async function searchGpa(event: SubmitEvent) {
    event.preventDefault();
    lookupError = '';
    lookupResult = null;
    const enteredValue = lookupValue ?? result.allocation_gpa.toFixed(2);
    const numeric = Number(enteredValue);
    if (!enteredValue.trim() || !Number.isFinite(numeric) || numeric < 0 || numeric > 4) {
      lookupError = 'Enter a GPA from 0.00 to 4.00.';
      return;
    }
    const normalized = numeric.toFixed(2);
    lookupValue = normalized;
    lookupLoading = true;
    try {
      lookupResult = await getAnonymousGpaLookup(normalized);
    } catch (error) {
      lookupError = error instanceof Error ? error.message : 'Unable to look up this GPA.';
    } finally {
      lookupLoading = false;
    }
  }

  async function toggleDepartment(department: DepartmentId) {
    if (selectedDepartment === department) {
      selectedDepartment = null;
      return;
    }

    selectedDepartment = department;
    departmentGroups = [];
    departmentError = '';
    departmentIncomplete = false;
    departmentLoading = true;
    try {
      const response = await getDepartmentGpas(department);
      if (selectedDepartment !== department) return;
      departmentGroups = response.groups;
      departmentIncomplete = response.incomplete;
    } catch (error) {
      if (selectedDepartment !== department) return;
      departmentError = error instanceof Error
        ? error.message
        : 'Unable to load department GPA information.';
    } finally {
      if (selectedDepartment === department) departmentLoading = false;
    }
  }
</script>

<section class="results" aria-labelledby="allocation-heading">
  <header class="results-header">
    <div>
      <p class="eyebrow">Live estimated allocation</p>
      <h2 id="allocation-heading">{resultHeading()}</h2>
      <p class="student">{result.name} · {result.index_number}</p>
    </div>
    <div class="gpa" aria-label={`Average GPA ${formatGpa(result.average_gpa)}, field-selection GPA ${result.allocation_gpa.toFixed(2)}`}>
      <span>Average GPA</span>
      <strong>{formatGpa(result.average_gpa)}</strong>
      <span class="selection-gpa-label">Field-selection GPA</span>
      <strong class="selection-gpa">{result.allocation_gpa.toFixed(2)}</strong>
      <details class="selection-gpa-help">
        <summary>What is field-selection GPA?</summary>
        <p>
          Your six-module average is rounded to two decimals for field selection. Students with
          the same two-decimal GPA compete using the two tie-break modules assigned to that
          department. Their grade points are combined using the modules' course credits.
        </p>
        <p>
          For example, Mechanical Engineering uses Mechanics and Mathematics. If the weighted
          tie-break score is also equal, all valid allocation outcomes remain possible.
        </p>
      </details>
    </div>
  </header>

  <section class="gpa-lookup" aria-labelledby="gpa-lookup-heading">
    <div>
      <h3 id="gpa-lookup-heading">Anonymous GPA lookup</h3>
      <p>See how many eligible students share a two-decimal field-selection GPA and their grouped estimated outcomes. Names and index numbers are never shown.</p>
    </div>
    <form onsubmit={searchGpa}>
      <label for="lookup-gpa">Two-decimal GPA</label>
      <div class="lookup-controls">
        <input id="lookup-gpa" class="lookup-input" type="number" min="0" max="4" step="0.01" inputmode="decimal" value={lookupValue ?? result.allocation_gpa.toFixed(2)} oninput={(event) => lookupValue = (event.currentTarget as HTMLInputElement).value} required />
        <button class="lookup-button" type="submit" disabled={lookupLoading}>{lookupLoading ? 'Searching…' : 'Search'}</button>
      </div>
    </form>
    {#if lookupError}<p class="lookup-error" role="alert">{lookupError}</p>{/if}
    {#if lookupResult}
      <div class="lookup-results" aria-live="polite">
        <p class="lookup-count"><strong>{lookupResult.count}</strong> of {lookupResult.total_students_processed} eligible students have a field-selection GPA of <strong>{lookupResult.gpa.toFixed(2)}</strong>.</p>
        {#if lookupResult.count === 0}
          <p>No matching allocation outcomes are available.</p>
        {:else}
          <div class="lookup-groups">
            {#each lookupResult.allocation_groups as group}
              <article>
                <strong>{group.count} student{group.count === 1 ? '' : 's'} · {group.allocation_status}</strong>
                <span>{lookupOutcome(group)}</span>
              </article>
            {/each}
          </div>
          {#if lookupResult.tiebreak_groups.length}
            <details class="lookup-tiebreaks">
              <summary>View anonymous tie-break module checks</summary>
              <div class="lookup-groups">
                {#each lookupResult.tiebreak_groups as group}
                  <article>
                    <strong>{getDepartmentName(group.department)} · {group.count} student{group.count === 1 ? '' : 's'}</strong>
                    {#each group.subjects as subject}
                      <span>{subjectNames[subject.subject]}: {subject.grade} ({subject.value.toFixed(1)})</span>
                    {/each}
                    <span>Credit-weighted score: {group.score.toFixed(4)} · {group.selection_status === 'selected' ? 'selected' : 'border outcome'}</span>
                    {#if group.score_tied}<em>The weighted score is also tied, so multiple valid outcomes remain.</em>{/if}
                  </article>
                {/each}
              </div>
            </details>
          {/if}
        {/if}
      </div>
    {/if}
  </section>

  <div class="metrics" aria-label="Allocation estimate details">
    <div class="metric">
      <span>Four-decimal GPA rank</span>
      <strong>#{result.student_rank}</strong>
    </div>
    <div class="metric">
      <span>Accuracy</span>
      <strong>{result.accuracy_percentage.toFixed(1)}%</strong>
      <small class="submission-count"
        >{result.total_students_processed} / 743 students submitted</small
      >
    </div>
    <div class="metric">
      <span>Confidence</span>
      <strong class={`confidence ${confidence.level}`}>{confidence.label}</strong>
      <details class="confidence-help">
        <summary>What is confidence?</summary>
        <p>Confidence is based on the percentage of the 743-student cohort that has submitted.</p>
        <ul>
          <li><strong>0–&lt;60%:</strong> Very Low</li>
          <li><strong>60–&lt;70%:</strong> Low</li>
          <li><strong>70–&lt;80%:</strong> Medium</li>
          <li><strong>80–&lt;90%:</strong> Average</li>
          <li><strong>90–&lt;95%:</strong> High</li>
          <li><strong>95–100%:</strong> Very High</li>
        </ul>
      </details>
    </div>
  </div>

  {#if result.allocation_status !== 'certain'}
    <aside class={`allocation-notice ${result.allocation_status}`} aria-label="Allocation border information">
      <strong>{result.allocation_status === 'border' ? 'Border estimate' : 'Unresolved estimate'}</strong>
      {#if result.border_departments.length}
        <p>Your result could be affected at: {departmentList(result.border_departments)}.</p>
      {/if}
      {#if result.possible_departments.length}
        <p>Possible allocations: {departmentList(result.possible_departments)}.</p>
      {/if}
      {#if result.guaranteed_department}
        <p>
          You are guaranteed {getDepartmentName(result.guaranteed_department)} or a higher-ranked
          preference.
        </p>
      {:else}
        <p>Subject marks are needed before a department can be guaranteed.</p>
      {/if}
      {#if result.allocation_explanation}<p>{result.allocation_explanation}</p>{/if}
    </aside>
  {/if}

  <aside class="disclaimer" aria-label="Important result disclaimer">
    <strong>Important:</strong>
    <span>{ALLOCATION_DISCLAIMER}</span>
  </aside>

  <div class="cutoffs">
    <h3>Current estimated cut-offs</h3>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Department</th>
            <th scope="col">Cut-off GPA</th>
          </tr>
        </thead>
        <tbody>
          {#each sortedDepartments as department}
            <tr class:assigned={department.id === result.assigned_department}>
              <td>
                <button
                  class="department-button"
                  type="button"
                  aria-expanded={selectedDepartment === department.id}
                  onclick={() => toggleDepartment(department.id)}
                >
                  {department.name}
                  <span>{selectedDepartment === department.id ? 'Hide GPA distribution' : 'View GPA distribution'}</span>
                </button>
                {#if department.id === result.assigned_department}
                  <span class="assigned-label">Your estimated allocation</span>
                {/if}
              </td>
              <td>
                {formatCutoff(result.cutoffs[department.id])}
                {#if result.cutoffs[department.id].status === 'open'}
                  <span class="open-note">Quota not filled</span>
                {/if}
                {#if result.cutoffs[department.id].incomplete}
                  <span class="open-note">Some tied outcomes could not be fully explored</span>
                {/if}
              </td>
            </tr>
            {#if selectedDepartment === department.id}
              <tr class="distribution-row">
                <td colspan="2">
                  <section class="distribution" aria-live="polite">
                    <h4>Anonymous two-decimal GPAs in {department.name}</h4>
                    <p class="distribution-note">
                      Student index numbers are never shown. A count range means unresolved ties
                      can change how many students with that GPA enter this department.
                    </p>
                    {#if departmentLoading}
                      <p>Loading GPA distribution…</p>
                    {:else if departmentError}
                      <p class="distribution-error" role="alert">{departmentError}</p>
                    {:else if departmentGroups.length === 0}
                      <p>No currently allocated students are available for this department.</p>
                    {:else}
                      <div class="gpa-groups">
                        {#each departmentGroups as group}
                          <div>
                            <strong>{group.gpa.toFixed(2)}</strong>
                            <span>
                              {group.min_count === group.max_count
                                ? `${group.min_count} student${group.min_count === 1 ? '' : 's'}`
                                : `${group.min_count}–${group.max_count} students`}
                            </span>
                          </div>
                        {/each}
                      </div>
                    {/if}
                    {#if departmentIncomplete}
                      <p class="distribution-warning">
                        This list is incomplete because the allocation exploration reached its
                        safety limit.
                      </p>
                    {/if}
                  </section>
                </td>
              </tr>
            {/if}
          {/each}
        </tbody>
      </table>
    </div>
  </div>

</section>

<style>
  .results {
    border: 1px solid #d1d5db;
    border-radius: 8px;
    background: #ffffff;
    padding: 28px;
  }

  .results-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 24px;
  }

  .eyebrow {
    margin-bottom: 6px;
    color: #1d4ed8;
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
  }

  h2 {
    margin-bottom: 8px;
    font-size: 1.6rem;
  }

  .student {
    margin-bottom: 0;
    color: #6b7280;
  }

  .gpa {
    min-width: 140px;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    background: #eff6ff;
    padding: 12px 16px;
    text-align: center;
  }

  .gpa span,
  .gpa strong,
  .metric span,
  .metric strong,
  .metric small {
    display: block;
  }

  .gpa span,
  .metric span,
  .metric small {
    color: #6b7280;
    font-size: 0.8rem;
  }

  .gpa strong {
    margin-top: 3px;
    color: #1e3a8a;
    font-size: 1.45rem;
  }

  .selection-gpa-label {
    margin-top: 10px;
    border-top: 1px solid #bfdbfe;
    padding-top: 9px;
  }

  .gpa .selection-gpa {
    color: #0f766e;
  }

  .selection-gpa-help {
    margin-top: 9px;
    text-align: left;
  }

  .selection-gpa-help summary {
    color: #1d4ed8;
    cursor: pointer;
    font-size: 0.75rem;
    font-weight: 700;
  }

  .selection-gpa-help p {
    width: 320px;
    margin: 8px 0 0;
    color: #475569;
    font-size: 0.78rem;
    line-height: 1.45;
  }

  .gpa-lookup {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(260px, 330px);
    gap: 18px 28px;
    margin-top: 20px;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    background: #f8fafc;
    padding: 16px;
  }

  .gpa-lookup h3,
  .gpa-lookup p {
    margin: 0;
  }

  .gpa-lookup > div > p {
    margin-top: 5px;
    color: #64748b;
    font-size: 0.84rem;
    line-height: 1.45;
  }

  .gpa-lookup form label {
    display: block;
    margin-bottom: 5px;
    font-size: 0.78rem;
    font-weight: 700;
  }

  .lookup-controls {
    display: flex;
    gap: 8px;
  }

  .lookup-input {
    min-width: 0;
    flex: 1;
    border: 1px solid #9ca3af;
    border-radius: 6px;
    padding: 9px 10px;
    font: inherit;
  }

  .lookup-button {
    border: 0;
    border-radius: 6px;
    background: #1d4ed8;
    padding: 9px 14px;
    color: #fff;
    cursor: pointer;
    font: inherit;
    font-weight: 700;
  }

  .lookup-button:disabled {
    cursor: wait;
    opacity: 0.65;
  }

  .lookup-error,
  .lookup-results {
    grid-column: 1 / -1;
  }

  .gpa-lookup .lookup-error {
    color: #991b1b;
  }

  .gpa-lookup .lookup-count {
    color: #1e3a8a;
  }

  .lookup-groups {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 10px;
    margin-top: 12px;
  }

  .lookup-groups article {
    display: grid;
    gap: 4px;
    border: 1px solid #dbeafe;
    border-radius: 7px;
    background: #fff;
    padding: 11px 12px;
    font-size: 0.82rem;
  }

  .lookup-groups article span {
    color: #475569;
  }

  .lookup-groups article em {
    color: #92400e;
  }

  .lookup-tiebreaks {
    margin-top: 14px;
  }

  .lookup-tiebreaks summary {
    width: fit-content;
    color: #1d4ed8;
    cursor: pointer;
    font-size: 0.84rem;
    font-weight: 700;
  }

  .metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 24px;
  }

  .metric {
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    background: #f9fafb;
    padding: 14px;
  }

  .metric strong {
    margin-top: 4px;
    font-size: 1.2rem;
  }

  .metric small {
    margin-top: 4px;
  }

  .metric .submission-count {
    margin-top: 6px;
    color: #4b5563;
    font-size: 0.95rem;
    font-weight: 600;
  }

  .confidence {
    width: fit-content;
    border-radius: 999px;
    padding: 5px 10px;
    font-size: 0.92rem !important;
  }

  .confidence.very-low {
    background: #fee2e2;
    color: #991b1b;
  }

  .confidence.low {
    background: #ffedd5;
    color: #9a3412;
  }

  .confidence.medium {
    background: #fef9c3;
    color: #854d0e;
  }

  .confidence.average {
    background: #dcfce7;
    color: #166534;
  }

  .confidence.high {
    background: #15803d;
    color: #ffffff;
  }

  .confidence.very-high {
    background: #14532d;
    color: #ffffff;
  }

  .confidence-help {
    margin-top: 8px;
    color: #4b5563;
    font-size: 0.78rem;
  }

  .confidence-help summary {
    width: fit-content;
    color: #1d4ed8;
    cursor: pointer;
    font-weight: 600;
  }

  .confidence-help p {
    margin: 8px 0 5px;
    line-height: 1.4;
  }

  .confidence-help ul {
    margin: 0;
    padding-left: 18px;
    line-height: 1.5;
  }

  .confidence-help li strong {
    display: inline;
    font-size: inherit;
  }

  .cutoffs {
    margin-top: 28px;
  }

  h3 {
    margin: 0 0 12px;
    font-size: 1.05rem;
  }

  .table-wrap {
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    border-bottom: 1px solid #e5e7eb;
    padding: 12px;
    text-align: left;
    vertical-align: top;
  }

  th {
    background: #f9fafb;
    color: #4b5563;
    font-size: 0.82rem;
  }

  th:last-child,
  td:last-child {
    width: 170px;
  }

  tr.assigned td {
    background: #eff6ff;
    font-weight: 600;
  }

  .department-button {
    border: 0;
    background: transparent;
    padding: 0;
    color: inherit;
    cursor: pointer;
    font: inherit;
    font-weight: inherit;
    text-align: left;
  }

  .department-button span {
    display: block;
    margin-top: 3px;
    color: #1d4ed8;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .distribution-row td {
    background: #f8fafc;
    padding: 0;
  }

  .distribution {
    padding: 16px 18px;
  }

  .distribution h4,
  .distribution p {
    margin: 0;
  }

  .distribution-note {
    margin-top: 5px !important;
    color: #64748b;
    font-size: 0.8rem;
  }

  .gpa-groups {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }

  .gpa-groups div {
    min-width: 112px;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    background: #ffffff;
    padding: 9px 11px;
  }

  .gpa-groups strong,
  .gpa-groups span {
    display: block;
  }

  .gpa-groups span {
    margin-top: 2px;
    color: #64748b;
    font-size: 0.76rem;
  }

  .distribution-error,
  .distribution-warning {
    margin-top: 10px !important;
    color: #991b1b;
  }

  .allocation-notice {
    margin-top: 20px;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    background: #fffbeb;
    padding: 14px 16px;
    color: #78350f;
  }

  .allocation-notice.unresolved {
    border-color: #f87171;
    background: #fef2f2;
    color: #991b1b;
  }

  .allocation-notice p {
    margin: 5px 0 0;
    line-height: 1.45;
  }

  .assigned-label,
  .open-note {
    display: block;
    margin-top: 3px;
    font-size: 0.75rem;
    font-weight: 400;
  }

  .assigned-label {
    color: #1d4ed8;
  }

  .open-note {
    color: #6b7280;
  }

  .disclaimer {
    display: flex;
    gap: 6px;
    margin-top: 24px;
    border: 1px solid #facc15;
    border-radius: 6px;
    background: #fefce8;
    padding: 14px;
    color: #713f12;
    font-size: 0.9rem;
    line-height: 1.5;
  }

  @media (max-width: 600px) {
    .results {
      padding: 20px;
    }

    .results-header {
      flex-direction: column;
    }

    .gpa {
      width: 100%;
    }

    .selection-gpa-help p {
      width: auto;
    }

    .gpa-lookup {
      grid-template-columns: 1fr;
    }

    .metrics {
      grid-template-columns: 1fr;
    }

    th,
    td {
      padding: 10px 8px;
    }

    .disclaimer {
      display: block;
    }

    .disclaimer strong {
      display: block;
      margin-bottom: 4px;
    }
  }
</style>
