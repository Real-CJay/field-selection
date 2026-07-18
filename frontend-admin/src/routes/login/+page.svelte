<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { authenticateStudent } from '$lib/student-auth';
  import { getStudentSession, saveStudentSession } from '$lib/session';
  import { studentRepository } from '$lib/student-repository';

  let indexNumber = $state('');
  let password = $state('');
  let loading = $state(false);
  let message = $state('');

  onMount(() => {
    if (getStudentSession()) goto('/preferences', { replaceState: true });
  });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    message = '';

    const result = await authenticateStudent(
      indexNumber,
      password,
      studentRepository.findStudent
    );

    if (!result.ok) {
      message = result.message;
      loading = false;
      return;
    }

    saveStudentSession({
      indexNumber: result.student.index_number,
      name: result.student.name
    });
    await goto('/preferences');
  }
</script>

<svelte:head><title>Student Login · Field Selection</title></svelte:head>

<main class="login-page">
  <section class="card login-card">
    <h1>Student Login</h1>
    <p class="muted">Enter your student index number and password.</p>

    <form onsubmit={submit}>
      <div class="field">
        <label for="index-number">Student index number</label>
        <input
          class="input"
          id="index-number"
          bind:value={indexNumber}
          autocomplete="username"
          required
        />
      </div>

      <div class="field">
        <label for="password">Password</label>
        <input
          class="input"
          id="password"
          type="password"
          bind:value={password}
          autocomplete="current-password"
          required
        />
      </div>

      {#if message}
        <div class="message" role="alert">{message}</div>
      {/if}

      <button class="button submit" type="submit" disabled={loading}>
        {loading ? 'Logging in…' : 'Login'}
      </button>
    </form>
  </section>
</main>

<style>
  .login-page {
    display: grid;
    min-height: 100vh;
    place-items: center;
    padding: 20px;
  }

  .login-card {
    width: min(400px, 100%);
  }

  .submit {
    width: 100%;
    margin-top: 24px;
  }
</style>
