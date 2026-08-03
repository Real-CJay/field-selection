<script lang="ts">
  import { goto } from '$app/navigation';
  import Turnstile from '$lib/components/Turnstile.svelte';
  import { authenticateAdmin } from '$lib/admin-client';
  import { clearAdminSession, setAdminSession } from '$lib/admin-session';
  import { getReturningStudentRoute } from '$lib/navigation';
  import { signOutStudentAuth } from '$lib/student-edit-auth';
  import { signInStudent } from '$lib/student-auth-client';
  import { saveStudentReadToken } from '$lib/student-api-session';
  import {
    clearStudentSession,
    saveStudentSession
  } from '$lib/session';
  import { studentRepository } from '$lib/student-repository';
  import { supabase } from '$lib/supabase';

  let indexNumber = $state('');
  let password = $state('');
  let loading = $state(false);
  let message = $state('');
  let turnstileToken = $state('');
  let turnstileVersion = $state(0);
  let isAdminUsername = $derived(indexNumber.trim().toLowerCase() === 'cjay');

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    message = '';

    const normalizedIndex = indexNumber.trim().toUpperCase();
    if (!turnstileToken) {
      message = 'Complete the security check first.';
      loading = false;
      return;
    }
    if (isAdminUsername) {
      try {
        const adminUsername = 'CJay';
        const result = await authenticateAdmin(adminUsername, password, turnstileToken);
        clearStudentSession();
        await signOutStudentAuth();
        setAdminSession({ username: result.username, token: result.admin_token });
        await goto('/admin');
      } catch (error) {
        message = error instanceof Error ? error.message : 'Invalid administrator credentials.';
      } finally {
        turnstileToken = '';
        turnstileVersion += 1;
        loading = false;
      }
      return;
    }

    try {
        clearAdminSession();
        await signOutStudentAuth();
        const login = await signInStudent(normalizedIndex, password, turnstileToken);
        if (login.access_mode === 'editable') {
        const { error } = await supabase.auth.setSession({
            access_token: login.access_token,
            refresh_token: login.refresh_token
        });
        if (error) throw error;
        } else {
          saveStudentReadToken(login.read_token);
        }
        saveStudentSession({
          indexNumber: login.index_number,
          name: login.name,
          accessMode: login.access_mode
        });
        try {
          await goto(await getReturningStudentRoute(login.index_number, studentRepository.getResults, studentRepository.getPreferences));
        } catch {
          await goto('/module-grades');
        }
      } catch (error) {
        await signOutStudentAuth();
        clearStudentSession();
        message = error instanceof Error ? error.message : 'Unable to sign in. Please try again.';
      } finally {
        turnstileToken = '';
        turnstileVersion += 1;
        loading = false;
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

      {#key turnstileVersion}
        <Turnstile
          action={isAdminUsername ? 'admin-auth' : 'student-auth'}
          onToken={(token) => { turnstileToken = token; }}
        />
      {/key}

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
