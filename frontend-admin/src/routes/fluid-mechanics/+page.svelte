<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { FLUID_MECHANICS_GRADES, isFluidMechanicsGrade } from '$lib/fluid-mechanics';
  import {
    clearStudentSession,
    getFluidMechanicsGrade,
    getStudentSession,
    saveFluidMechanicsGrade
  } from '$lib/session';
  import type { FluidMechanicsGrade, StudentSession } from '$lib/types';

  let session = $state<StudentSession | null>(null);
  let grade = $state<FluidMechanicsGrade | ''>('');
  let message = $state('');

  onMount(async () => {
    session = getStudentSession();
    if (!session) {
      await goto('/login', { replaceState: true });
      return;
    }
    grade = getFluidMechanicsGrade() ?? '';
  });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    message = '';

    if (!isFluidMechanicsGrade(grade)) {
      message = 'Select your Fluid Mechanics grade.';
      return;
    }

    saveFluidMechanicsGrade(grade);
    await goto('/preferences');
  }

  function logout() {
    clearStudentSession();
    goto('/login');
  }
</script>

<svelte:head><title>Fluid Mechanics Grade · Field Selection</title></svelte:head>

<main class="grade-page">
  <section class="card grade-card">
    <div class="grade-header">
      <div>
        <h1>Fluid Mechanics Grade</h1>
        {#if session}
          <p class="muted">{session.name} · {session.indexNumber}</p>
        {/if}
      </div>
      <button class="button secondary" type="button" onclick={logout}>Logout</button>
    </div>

    <p class="intro">Select the grade you received for the Fluid Mechanics module.</p>

    <form onsubmit={submit}>
      <div class="field">
        <label for="fluid-mechanics-grade">Grade</label>
        <select
          class="select"
          id="fluid-mechanics-grade"
          bind:value={grade}
          required
        >
          <option value="">Select your grade</option>
          {#each FLUID_MECHANICS_GRADES as option}
            <option value={option}>{option}</option>
          {/each}
        </select>
      </div>

      {#if message}
        <div class="message" role="alert">{message}</div>
      {/if}

      <button class="button continue" type="submit">Continue to Preferences</button>
    </form>

    <p class="temporary-note">
      Your grade is saved for this browser session. Backend submission will be connected after the
      API details are confirmed.
    </p>
  </section>
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
