<script lang="ts">
  import {
    ALLOCATION_DISCLAIMER,
    formatCutoff,
    formatGpa,
    getConfidence,
    getDepartmentName
  } from '$lib/allocation';
  import { DEPARTMENTS } from '$lib/preferences';
  import type { AllocationResult } from '$lib/types';

  let { result }: { result: AllocationResult } = $props();
  let confidence = $derived(getConfidence(result.accuracy_percentage));
</script>

<section class="results" aria-labelledby="allocation-heading">
  <header class="results-header">
    <div>
      <p class="eyebrow">Live estimated allocation</p>
      <h2 id="allocation-heading">{getDepartmentName(result.assigned_department)}</h2>
      <p class="student">{result.name} · {result.index_number}</p>
    </div>
    <div class="gpa" aria-label={`Average GPA ${formatGpa(result.average_gpa)}`}>
      <span>Average GPA</span>
      <strong>{formatGpa(result.average_gpa)}</strong>
    </div>
  </header>

  <div class="metrics" aria-label="Allocation estimate details">
    <div class="metric">
      <span>Student rank</span>
      <strong>#{result.student_rank}</strong>
    </div>
    <div class="metric">
      <span>Accuracy</span>
      <strong>{result.accuracy_percentage.toFixed(1)}%</strong>
      <small>{result.total_students_processed} / 743 students submitted</small>
    </div>
    <div class="metric">
      <span>Confidence</span>
      <strong class={`confidence ${confidence.level}`}>{confidence.label}</strong>
    </div>
  </div>

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
          {#each DEPARTMENTS as department}
            <tr class:assigned={department.id === result.assigned_department}>
              <td>
                {department.name}
                {#if department.id === result.assigned_department}
                  <span class="assigned-label">Your estimated allocation</span>
                {/if}
              </td>
              <td>
                {formatCutoff(result.cutoffs[department.id])}
                {#if result.cutoffs[department.id] === null}
                  <span class="open-note">Quota not filled</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  </div>

  <aside class="disclaimer" aria-label="Important result disclaimer">
    <strong>Important:</strong>
    <span>{ALLOCATION_DISCLAIMER}</span>
  </aside>
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
