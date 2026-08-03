<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import StudentCredentialModal from '$lib/components/StudentCredentialModal.svelte';
  import {
    MODULE_GRADES,
    getEditableGradeFromGpa,
    isModuleGrade
  } from '$lib/module-grades';
  import {
    clearStudentSession,
    getModuleGrades,
    getStudentSession
  } from '$lib/session';
  import type { ModuleGrade, StudentSession } from '$lib/types';
  import { studentRepository } from '$lib/student-repository';
  import { clearStudentApiSession, getStudentApiSession } from '$lib/student-api-session';
  import { getStudentWritesEnabled, isStudentWriteAuthError, saveStudentModuleGrades } from '$lib/student-write-client';
  import { GRADE_EDITING_UNAVAILABLE } from '$lib/student-write-status';

  let session = $state<StudentSession | null>(null);
  let fluidMechanics = $state<ModuleGrade | ''>('');
  let mechanics = $state<ModuleGrade | ''>('');
  let message = $state('');
  let authModalOpen = $state(false);
  let saving = $state(false);

  onMount(async () => {
    session = getStudentSession();
    if (!session) {
      await goto('/login', { replaceState: true });
      return;
    }

    const saved = getModuleGrades();
    if (saved) {
      fluidMechanics = saved.fluidMechanics;
      mechanics = saved.mechanics;
    } else {
      try {
        const results = await studentRepository.getResults(session.indexNumber);
        const fluidGrade = getEditableGradeFromGpa(results?.fluids);
        const mechanicsGrade = getEditableGradeFromGpa(results?.mechanics);
        if (isModuleGrade(fluidGrade)) fluidMechanics = fluidGrade;
        if (isModuleGrade(mechanicsGrade)) mechanics = mechanicsGrade;
      } catch {
        message = 'Unable to load your saved grades. You can still select them again.';
      }
    }
  });

  async function saveCurrentGrades() {
    if (!isModuleGrade(fluidMechanics) || !isModuleGrade(mechanics)) return;
    saving = true;
    message = '';
    try {
      await saveStudentModuleGrades({ fluidMechanics, mechanics });
      await goto('/preferences');
    } catch (error) {
      if (isStudentWriteAuthError(error)) {
        authModalOpen = true;
        session = session ? { ...session, accessMode: 'read-only' } : session;
        return;
      }
      message = error instanceof Error ? error.message : 'Unable to save module grades.';
    } finally {
      saving = false;
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!session) return;
    message = '';

    if (!isModuleGrade(fluidMechanics) || !isModuleGrade(mechanics)) {
      message = 'Select both your Fluid Mechanics and Mechanics grades.';
      return;
    }
    if (getStudentApiSession()?.accessMode === 'editable') {
      await saveCurrentGrades();
      return;
    }
    try {
      if (!await getStudentWritesEnabled()) {
        message = GRADE_EDITING_UNAVAILABLE;
        return;
      }
    } catch (error) {
      message = error instanceof Error ? error.message : 'Please log in again.';
      return;
    }
    authModalOpen = true;
  }

  async function saveAfterAuthentication() {
    authModalOpen = false;
    session = getStudentSession();
    await saveCurrentGrades();
  }

  async function logout() {
    clearStudentSession();
    clearStudentApiSession();
    await goto('/login');
  }
</script>

<svelte:head><title>Module Grades · Field Selection</title></svelte:head>

<main class="grade-page">
  <section class="card grade-card">
    <div class="grade-header">
      <div>
        <h1>Module Grades</h1>
        {#if session}
          <p class="muted">{session.name} · {session.indexNumber} · <span class="access-badge">{session.accessMode === 'editable' ? 'Editable' : 'Read-only'}</span></p>
        {/if}
      </div>
      <button class="button secondary" type="button" onclick={logout}>Logout</button>
    </div>

    <p class="intro">Select the grades you received for both modules.</p>

    <form onsubmit={submit}>
      <div class="field">
        <label for="fluid-mechanics-grade">Fluid Mechanics</label>
        <select
          class="select"
          id="fluid-mechanics-grade"
          bind:value={fluidMechanics}
          required
        >
          <option value="">Select your grade</option>
          {#each MODULE_GRADES as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </div>

      <div class="field">
        <label for="mechanics-grade">Mechanics</label>
        <select class="select" id="mechanics-grade" bind:value={mechanics} required>
          <option value="">Select your grade</option>
          {#each MODULE_GRADES as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </div>

      {#if message}
        <div class="message" role="alert">{message}</div>
      {/if}

      <button class="button continue" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Continue to Preferences'}</button>
    </form>

    <p class="temporary-note">
      Your grades are saved securely with your student results.
    </p>
  </section>

</main>

{#if session}
  <StudentCredentialModal
    open={authModalOpen}
    indexNumber={session.indexNumber}
    onAuthenticated={saveAfterAuthentication}
    onCancel={() => { authModalOpen = false; }}
  />
{/if}

<style>
  .grade-page {
    display: grid;
    min-height: 100vh;
    place-items: center;
    padding: 20px;
  }

  .grade-card {
    width: min(520px, 100%);
  }

  .grade-header {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 20px;
  }

  .grade-header h1,
  .grade-header p {
    margin-bottom: 0;
  }

  .intro {
    margin-top: 24px;
  }

  .continue {
    width: 100%;
    margin-top: 24px;
  }

  .temporary-note {
    margin: 20px 0 0;
    color: #6b7280;
    font-size: 0.82rem;
    line-height: 1.5;
  }

  .access-badge { font-weight: 700; color: #1d4ed8; }

  @media (max-width: 520px) {
    .grade-header {
      align-items: flex-start;
    }
  }
</style>
