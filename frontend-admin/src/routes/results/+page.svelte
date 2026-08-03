<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { createConfiguredAllocationClient } from '$lib/allocation-client';
  import { getAllocationErrorState } from '$lib/allocation';
  import AllocationLoading from '$lib/components/AllocationLoading.svelte';
  import AllocationResults from '$lib/components/AllocationResults.svelte';
  import AllocationStatus from '$lib/components/AllocationStatus.svelte';
  import StudentCredentialModal from '$lib/components/StudentCredentialModal.svelte';
  import { MODULE_GRADES, getGradeFromGpa, hasSubmittedModuleGrades } from '$lib/module-grades';
  import { getStudentResultsEntryRoute } from '$lib/navigation';
  import {
    clearStudentSession,
    getStudentSession
  } from '$lib/session';
  import { clearStudentApiSession, getStudentApiSession } from '$lib/student-api-session';
  import { studentRepository } from '$lib/student-repository';
  import { CORRECTION_REQUESTS_UNAVAILABLE } from '$lib/student-write-status';
  import { getStudentWritesEnabled, isStudentWriteAuthError, submitStudentCorrection } from '$lib/student-write-client';
  import type {
    AllocationResult,
    StudentResults,
    StudentSession
  } from '$lib/types';
  import type { CorrectableModule, ModuleGrade } from '$lib/types';

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
  let correctionModule = $state<CorrectableModule>('cse');
  let requestedGrade = $state<ModuleGrade | ''>('');
  let correctionMessage = $state('');
  let authModalOpen = $state(false);
  let correctionSending = $state(false);

  onMount(async () => {
    const activeSession = getStudentSession();
    session = activeSession;
    if (!activeSession) {
      await goto('/login', { replaceState: true });
      return;
    }

    try {
      const [preferences, savedResults] = await Promise.all([
        studentRepository.getPreferences(activeSession.indexNumber),
        studentRepository.getResults(activeSession.indexNumber)
      ]);
      const verifiedRoute = getStudentResultsEntryRoute(
        true,
        hasSubmittedModuleGrades(savedResults),
        Boolean(preferences)
      );
      if (verifiedRoute !== '/results') {
        await goto(verifiedRoute, { replaceState: true });
        return;
      }
      studentResults = savedResults;
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

  async function logout() {
    clearStudentSession();
    clearStudentApiSession();
    await goto('/login');
  }

  async function sendCurrentCorrection() {
    if (!requestedGrade) return;
    correctionSending = true;
    correctionMessage = '';
    try {
      await submitStudentCorrection(correctionModule, requestedGrade);
      correctionMessage = 'Your grade correction request was sent for admin review.';
      requestedGrade = '';
    } catch (error) {
      if (isStudentWriteAuthError(error)) {
        authModalOpen = true;
        session = session ? { ...session, accessMode: 'read-only' } : session;
        return;
      }
      correctionMessage = error instanceof Error ? error.message : 'Unable to send the request.';
    } finally {
      correctionSending = false;
    }
  }

  async function requestCorrection(event: SubmitEvent) {
    event.preventDefault();
    if (!session || !requestedGrade) return;
    if (getStudentApiSession()?.accessMode === 'editable') {
      await sendCurrentCorrection();
      return;
    }
    try {
      if (!await getStudentWritesEnabled()) {
        correctionMessage = CORRECTION_REQUESTS_UNAVAILABLE;
        return;
      }
    } catch (error) {
      correctionMessage = error instanceof Error ? error.message : 'Please log in again.';
      return;
    }
    authModalOpen = true;
  }

  async function sendAfterAuthentication() {
    authModalOpen = false;
    session = getStudentSession();
    await sendCurrentCorrection();
  }
</script>

<svelte:head><title>Your Results · Field Selection</title></svelte:head>

<main class="page">
  <header class="page-header">
    <div>
      <h1>Your Results</h1>
      {#if session}
        <p class="muted">{session.name} · {session.indexNumber} · <span class="access-badge">{session.accessMode === 'editable' ? 'Editable' : 'Read-only'}</span></p>
      {/if}
    </div>
    <div class="actions">
      <a class="button secondary" href="/module-grades">Edit Fluid/Mechanics grades</a>
      <a class="button secondary" href="/preferences">Edit preferences</a>
      <button class="button secondary" type="button" onclick={logout}>Logout</button>
    </div>
  </header>

  <div class="allocation-section">
    {#if allocation}
      <AllocationResults result={allocation} />
    {:else if allocationState === 'loading'}
      <AllocationLoading />
    {:else}
      <AllocationStatus state={allocationState} />
    {/if}
  </div>

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
      <section class="correction" aria-labelledby="correction-heading">
        <h3 id="correction-heading">Request a grade correction</h3>
        <p class="result-note">
          For CSE, Mathematics, Electrical, or Material Science, send the correct grade for admin
          review. Fluid Mechanics and Mechanics can be edited directly above.
        </p>
        <form class="correction-form" onsubmit={requestCorrection}>
          <label>
            Module
            <select class="select" bind:value={correctionModule}>
              <option value="cse">CSE</option>
              <option value="maths">Mathematics</option>
              <option value="electrical">Electrical</option>
              <option value="material">Material Science</option>
            </select>
          </label>
          <label>
            Correct grade
            <select class="select" bind:value={requestedGrade} required>
              <option value="">Select grade</option>
              {#each MODULE_GRADES as grade}<option value={grade}>{grade}</option>{/each}
            </select>
          </label>
          <button class="button" type="submit" disabled={correctionSending}>{correctionSending ? 'Sending…' : 'Send request'}</button>
        </form>
        {#if correctionMessage}<p class="correction-message" role="status">{correctionMessage}</p>{/if}
      </section>
    {/if}
  </section>

</main>

{#if session}
  <StudentCredentialModal
    open={authModalOpen}
    indexNumber={session.indexNumber}
    onAuthenticated={sendAfterAuthentication}
    onCancel={() => { authModalOpen = false; }}
  />
{/if}

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

  .correction {
    margin-top: 24px;
    border-top: 1px solid #e5e7eb;
    padding-top: 20px;
  }

  .correction h3 { margin: 0; font-size: 1rem; }
  .correction-form { display: flex; align-items: end; gap: 12px; margin-top: 16px; }
  .correction-form label { flex: 1; font-size: 0.85rem; font-weight: 600; }
  .correction-form .select { margin-top: 6px; }
  .correction-message { margin: 14px 0 0; color: #166534; }

  .status {
    margin: 18px 0 0;
    color: #6b7280;
  }

  .access-badge { font-weight: 700; color: #1d4ed8; }

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

    .correction-form { align-items: stretch; flex-direction: column; }

    .actions .button {
      flex: 1;
      justify-content: center;
    }
  }
</style>
