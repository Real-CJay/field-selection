<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import StudentWriteAuthModal from '$lib/components/StudentWriteAuthModal.svelte';
  import {
    GRADE_TO_GPA,
    MODULE_GRADES,
    getEditableGradeFromGpa,
    isModuleGrade
  } from '$lib/module-grades';
  import {
    clearStudentSession,
    getModuleGrades,
    getStudentSession,
    saveModuleGrades
  } from '$lib/session';
  import type { ModuleGrade, StudentSession } from '$lib/types';
  import { studentRepository } from '$lib/student-repository';
  import { hasEditableSession, signOutStudentAuth } from '$lib/student-edit-auth';

  let session = $state<StudentSession | null>(null);
  let fluidMechanics = $state<ModuleGrade | ''>('');
  let mechanics = $state<ModuleGrade | ''>('');
  let message = $state('');
  let saving = $state(false);
  let showAuthentication = $state(false);

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

  async function saveGrades() {
    if (!session) return;
    if (!isModuleGrade(fluidMechanics) || !isModuleGrade(mechanics)) return;
    saving = true;
    try {
      await studentRepository.saveGrades(
        session.indexNumber,
        GRADE_TO_GPA[fluidMechanics],
        GRADE_TO_GPA[mechanics]
      );
      saveModuleGrades({ fluidMechanics, mechanics });
      await goto('/preferences');
    } catch {
      message = 'Unable to save grades. Please try again.';
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
    if (!await hasEditableSession(session.indexNumber)) {
      showAuthentication = true;
      return;
    }
    await saveGrades();
  }

  async function authenticatedAndSave() {
    showAuthentication = false;
    await saveGrades();
  }

  async function logout() {
    clearStudentSession();
    await signOutStudentAuth();
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
          <p class="muted">{session.name} · {session.indexNumber}</p>
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

      <button class="button continue" type="submit" disabled={saving}>
        {saving ? 'Saving…' : 'Continue to Preferences'}
      </button>
    </form>

    <p class="temporary-note">
      Your grades are saved securely with your student results.
    </p>
  </section>

  {#if session}
    <StudentWriteAuthModal
      open={showAuthentication}
      indexNumber={session.indexNumber}
      onAuthenticated={authenticatedAndSave}
      onCancel={() => { showAuthentication = false; }}
      onLogout={logout}
    />
  {/if}
</main>

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

  @media (max-width: 520px) {
    .grade-header {
      align-items: flex-start;
    }
  }
</style>
