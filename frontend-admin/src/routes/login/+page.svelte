<script lang="ts">
  import { goto } from '$app/navigation';
  import { authenticateAdmin } from '$lib/admin-client';
  import { clearAdminSession, setAdminSession } from '$lib/admin-session';
  import StudentCredentialModal from '$lib/components/StudentCredentialModal.svelte';
  import { getReturningStudentRoute } from '$lib/navigation';
  import { signInStudent, tokenFromLogin } from '$lib/student-auth-client';
  import { clearStudentApiSession, saveStudentApiSession } from '$lib/student-api-session';
  import {
    clearStudentSession,
    saveStudentSession
  } from '$lib/session';
  import { studentRepository } from '$lib/student-repository';

  let indexNumber = $state('');
  let password = $state('');
  let loading = $state(false);
  let message = $state('');
  let recoveryModalOpen = $state(false);
  let isAdminUsername = $derived(indexNumber.trim().toLowerCase() === 'cjay');

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    message = '';

    const normalizedIndex = indexNumber.trim().toUpperCase();
    if (isAdminUsername) {
      try {
        const adminUsername = 'CJay';
        const result = await authenticateAdmin(adminUsername, password);
        clearStudentSession();
        clearStudentApiSession();
        setAdminSession({ username: result.username, token: result.admin_token });
        await goto('/admin');
      } catch (error) {
        message = error instanceof Error ? error.message : 'Invalid administrator credentials.';
      } finally {
        loading = false;
      }
      return;
    }

    try {
      clearAdminSession();
      clearStudentApiSession();
      const login = await signInStudent(normalizedIndex, password);
      saveStudentApiSession({ accessMode: login.access_mode, token: tokenFromLogin(login) });
      saveStudentSession({
        indexNumber: login.index_number,
        name: login.name,
        accessMode: login.access_mode
      });
      try {
        await goto(await getReturningStudentRoute(
          login.index_number,
          studentRepository.getResults,
          studentRepository.getPreferences
        ));
      } catch {
        await goto('/module-grades');
      }
    } catch (error) {
      clearStudentApiSession();
      clearStudentSession();
      message = error instanceof Error ? error.message : 'Unable to sign in. Please try again.';
    } finally {
      loading = false;
    }
  }

  function openRecoveryModal() {
    if (isAdminUsername) return;
    if (!indexNumber.trim()) {
      message = 'Enter your student index number first.';
      return;
    }
    message = '';
    recoveryModalOpen = true;
  }

  async function continueAfterRecovery() {
    recoveryModalOpen = false;
    const normalizedIndex = indexNumber.trim().toUpperCase();
    try {
      await goto(await getReturningStudentRoute(
        normalizedIndex,
        studentRepository.getResults,
        studentRepository.getPreferences
      ));
    } catch {
      await goto('/module-grades');
    }
  }
</script>

<svelte:head><title>Student Login · Field Selection</title></svelte:head>

<main class="login-page">
  <section class="card login-card">
    <h1>Student Login</h1>
    <p class="muted">Enter your student index number and password.</p>

    <form onsubmit={submit}>
      <div class="field">
        <label for="index-number">Student index number or admin username</label>
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
      {#if !isAdminUsername}
        <button class="forgot" type="button" onclick={openRecoveryModal}>Forgot personal password?</button>
      {/if}
    </form>
  </section>
</main>

<StudentCredentialModal
  open={recoveryModalOpen}
  indexNumber={indexNumber.trim().toUpperCase()}
  initialMode="recovery"
  onAuthenticated={continueAfterRecovery}
  onCancel={() => { recoveryModalOpen = false; }}
/>

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

  .forgot {
    width: 100%;
    margin-top: 16px;
    border: 0;
    background: transparent;
    color: #1d4ed8;
    cursor: pointer;
    text-decoration: underline;
  }
</style>
