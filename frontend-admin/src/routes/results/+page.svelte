<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { createConfiguredAllocationClient } from '$lib/allocation-client';
  import { getAllocationErrorState } from '$lib/allocation';
  import AllocationLoading from '$lib/components/AllocationLoading.svelte';
  import AllocationResults from '$lib/components/AllocationResults.svelte';
  import AllocationStatus from '$lib/components/AllocationStatus.svelte';
  import { getGradeFromGpa } from '$lib/module-grades';
  import { getStudentResultsEntryRoute } from '$lib/navigation';
  import {
    clearStudentSession,
    getModuleGrades,
    getStudentSession
  } from '$lib/session';
  import { studentRepository } from '$lib/student-repository';
  import type {
    AllocationResult,
    StudentResults,
    StudentSession
  } from '$lib/types';

  const subjects = [
    { key: 'cse', label: 'CSE' },
    { key: 'maths', label: 'Mathematics' },
    { key: 'electrical', label: 'Electrical' },
    { key: 'fluids', label: 'Fluid Mechanics' },
    { key: 'mechanics', label: 'Mechanics' },
    { key: 'material', label: 'Material Science' }
  ] as const;

  let session = $state<StudentSession | null>(null);
  let studentResults = $state<StudentResults | null>(null);
  let allocation = $state<AllocationResult | null>(null);
  let resultsLoading = $state(true);
  let allocationState = $state<'loading' | 'not-found' | 'error'>('loading');
  let resultsError = $state('');

  onMount(async () => {
    const activeSession = getStudentSession();
    session = activeSession;
    const initialRoute = getStudentResultsEntryRoute(
      Boolean(activeSession),
      Boolean(getModuleGrades()),
      true
    );
    if (initialRoute !== '/results') {
      await goto(initialRoute, { replaceState: true });
      return;
    }
    if (!activeSession) return;

    try {
      const preferences = await studentRepository.getPreferences(activeSession.indexNumber);
      const verifiedRoute = getStudentResultsEntryRoute(true, true, Boolean(preferences));
      if (verifiedRoute !== '/results') {
        await goto(verifiedRoute, { replaceState: true });
        return;
      }
      studentResults = await studentRepository.getResults(activeSession.indexNumber);
      if (!studentResults) resultsError = 'No module results were found for this student.';
    } catch {
      resultsError = 'Unable to load your module results. Please try again.';
    } finally {
      resultsLoading = false;
    }

    try {
      const client = createConfiguredAllocationClient(window.fetch.bind(window));
      allocation = await client.getAllocation(activeSession.indexNumber);
    } catch (error) {
      allocationState = getAllocationErrorState(error);
    }
  });

  function logout() {
    clearStudentSession();
    goto('/login');
  }
</script>

<svelte:head><title>Your Results · Field Selection</title></svelte:head>

<main class="page">
  <header class="page-header">
    <div>
      <h1>Your Results</h1>
      {#if session}
        <p class="muted">{session.name} · {session.indexNumber}</p>
      {/if}
    </div>
    <div class="actions">
      <a class="button secondary" href="/preferences">Edit preferences</a>
      <button class="button secondary" type="button" onclick={logout}>Logout</button>
    </div>
  </header>

  <section class="card subject-card" aria-labelledby="module-results-heading">
    <h2 id="module-results-heading">Module grades</h2>
    {#if resultsLoading}
      <p class="status">Loading module grades…</p>
    {:else if resultsError}
      <div class="message" role="alert">{resultsError}</div>
    {:else if studentResults}
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th scope="col">Module</th><th scope="col">Grade</th></tr>
          </thead>
          <tbody>
            {#each subjects as subject}
              <tr>
                <td>{subject.label}</td>
                <td>{getGradeFromGpa(studentResults[subject.key])}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
      <p class="result-note">If these module grades are incorrect, contact the administrator.</p>
    {/if}
  </section>

  <div class="allocation-section">
    {#if allocation}
      <AllocationResults result={allocation} />
    {:else if allocationState === 'loading'}
      <AllocationLoading />
    {:else}
      <AllocationStatus state={allocationState} />
    {/if}
  </div>
</main>

<style>
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
    margin-bottom: 20px;
  }

  .page-header h1,
  .page-header p {
    margin-bottom: 0;
  }

  .actions {
    display: flex;
    gap: 10px;
  }

  a.button {
    display: inline-flex;
    align-items: center;
    text-decoration: none;
  }

  h2 {
    margin-bottom: 8px;
    font-size: 1.25rem;
  }

  .table-wrap {
    margin-top: 18px;
    overflow-x: auto;
  }

  table {
    width: 100%;
    border-collapse: collapse;
  }

  th,
  td {
    border-bottom: 1px solid #e5e7eb;
    padding: 11px 12px;
    text-align: left;
  }

  th {
    background: #f9fafb;
    font-size: 0.85rem;
  }

  th:last-child,
  td:last-child {
    width: 180px;
  }

  .result-note {
    margin: 16px 0 0;
    color: #6b7280;
    font-size: 0.85rem;
  }

  .status {
    margin: 18px 0 0;
    color: #6b7280;
  }

  .allocation-section {
    margin-top: 20px;
  }

  @media (max-width: 640px) {
    .page-header {
      align-items: flex-start;
      flex-direction: column;
    }

    .actions {
      width: 100%;
    }

    .actions .button {
      flex: 1;
      justify-content: center;
    }
  }
</style>
