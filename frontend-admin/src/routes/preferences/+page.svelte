<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import {
    DEPARTMENTS,
    emptyRankings,
    preferencesToRankings,
    validateRankings
  } from '$lib/preferences';
  import { hasSubmittedModuleGrades } from '$lib/module-grades';
  import {
    clearStudentSession,
    getModuleGrades,
    getStudentSession
  } from '$lib/session';
  import { clearStudentReadToken } from '$lib/student-api-session';
  import { studentRepository } from '$lib/student-repository';
  import { PREFERENCE_EDITING_UNAVAILABLE } from '$lib/student-write-status';
  import type { StudentRankings, StudentSession } from '$lib/types';

  const rankOptions = Array.from({ length: DEPARTMENTS.length }, (_, index) => index + 1);

  let session = $state<StudentSession | null>(null);
  let rankings = $state<StudentRankings>(emptyRankings());
  let loading = $state(true);
  let errorMessage = $state('');

  let usedRanks = $derived(
    new Set(Object.values(rankings).filter((rank): rank is number => typeof rank === 'number'))
  );

  onMount(async () => {
    session = getStudentSession();
    if (!session) {
      await goto('/login', { replaceState: true });
      return;
    }
    try {
      const [saved, results] = await Promise.all([
        studentRepository.getPreferences(session.indexNumber),
        studentRepository.getResults(session.indexNumber)
      ]);
      if (!getModuleGrades() && !hasSubmittedModuleGrades(results)) {
        await goto('/module-grades', { replaceState: true });
        return;
      }
      if (saved) rankings = preferencesToRankings(saved);
    } catch {
      errorMessage = 'Unable to load saved preferences. Please try again.';
    } finally {
      loading = false;
    }
  });

  function updateRank(department: keyof StudentRankings, event: Event) {
    const value = (event.currentTarget as HTMLSelectElement).value;
    rankings[department] = value === '' ? '' : Number(value);
    errorMessage = '';
  }

  function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!session) return;

    errorMessage = validateRankings(rankings) ?? '';
    if (errorMessage) return;

    errorMessage = PREFERENCE_EDITING_UNAVAILABLE;
  }

  async function logout() {
    clearStudentSession();
    clearStudentReadToken();
    await goto('/login');
  }
</script>

<svelte:head><title>Field Preferences · Field Selection</title></svelte:head>

<main class="page">
  <header class="page-header">
    <div>
      <h1>Field Selection</h1>
      {#if session}
        <p class="muted">{session.name} · {session.indexNumber}</p>
      {/if}
    </div>
    <button class="button secondary" type="button" onclick={logout}>Logout</button>
  </header>

  <section class="card">
    <h2>Rank your preferences</h2>
    <p class="muted">
      Assign each department a different rank from 1 to {DEPARTMENTS.length}. Rank 1 is your first
      choice.
    </p>

    {#if loading}
      <p class="status">Loading preferences…</p>
    {:else}
      <form onsubmit={submit}>
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>Department</th><th>Rank</th></tr>
            </thead>
            <tbody>
              {#each DEPARTMENTS as department}
                <tr>
                  <td>{department.name}</td>
                  <td>
                    <select
                      class="select rank-select"
                      aria-label={`Rank for ${department.name}`}
                      value={rankings[department.id]}
                      onchange={(event) => updateRank(department.id, event)}
                      required
                    >
                      <option value="">Select</option>
                      {#each rankOptions as rank}
                        <option
                          value={rank}
                          disabled={usedRanks.has(rank) && rankings[department.id] !== rank}
                        >{rank}</option>
                      {/each}
                    </select>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>

        {#if errorMessage}
          <div class="message" role="alert">{errorMessage}</div>
        {/if}
        <button class="button save" type="submit">Save Preferences</button>
      </form>
    {/if}
  </section>

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

  h2 {
    margin-bottom: 8px;
    font-size: 1.25rem;
  }

  .table-wrap {
    margin-top: 24px;
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
  }

  th {
    background: #f9fafb;
    font-size: 0.85rem;
  }

  .rank-select {
    width: 110px;
  }

  .save {
    margin-top: 22px;
  }

  .status {
    margin: 24px 0 0;
    color: #6b7280;
  }

  @media (max-width: 520px) {
    .page-header {
      align-items: flex-start;
    }

    th,
    td {
      padding: 10px 8px;
    }

    .rank-select {
      width: 94px;
    }

    .save {
      width: 100%;
    }
  }
</style>
