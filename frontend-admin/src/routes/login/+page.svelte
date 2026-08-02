<script lang="ts">
  import { goto } from '$app/navigation';
  import Turnstile from '$lib/components/Turnstile.svelte';
  import { authenticateAdmin } from '$lib/admin-client';
  import { setAdminCredentials } from '$lib/admin-session';
  import { getReturningStudentRoute } from '$lib/navigation';
  import { authenticateStudent } from '$lib/student-auth';
  import { signOutStudentAuth } from '$lib/student-edit-auth';
  import { getAuthenticatedStudent, signInStudentWithPassword } from '$lib/student-auth-client';
  import { STUDENT_PASSWORD } from '$lib/credentials';
  import { isMaintenancePreviewStudent } from '$lib/maintenance-access';
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
    if (isAdminUsername) {
      try {
        const adminUsername = 'CJay';
        await authenticateAdmin(adminUsername, password);
        clearStudentSession();
        await signOutStudentAuth();
        setAdminCredentials({ username: adminUsername, password });
        await goto('/admin');
      } catch (error) {
        message = error instanceof Error ? error.message : 'Invalid administrator credentials.';
      } finally {
        loading = false;
      }
      return;
    }

    if (!isMaintenancePreviewStudent(normalizedIndex)) {
      clearStudentSession();
      await signOutStudentAuth();
      await goto('/', { replaceState: true });
      return;
    }

    if (password !== STUDENT_PASSWORD) {
      if (!turnstileToken) {
        message = 'Complete the security check first.';
        loading = false;
        return;
      }
      try {
        const tokens = await signInStudentWithPassword(normalizedIndex, password, turnstileToken);
        const { error } = await supabase.auth.setSession({
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token
        });
        if (error) throw error;
        const student = await getAuthenticatedStudent(tokens.access_token);
        if (student.index_number !== normalizedIndex) throw new Error('Student identity mismatch.');
        saveStudentSession({
          indexNumber: student.index_number,
          name: student.name,
          accessMode: 'editable'
        });
        try {
          await goto(await getReturningStudentRoute(student.index_number, studentRepository.getResults, studentRepository.getPreferences));
        } catch {
          await goto('/preferences');
        }
      } catch (error) {
        await signOutStudentAuth();
        message = error instanceof Error ? error.message : 'Unable to sign in. Please try again.';
        turnstileToken = '';
        turnstileVersion += 1;
        loading = false;
      }
      return;
    }

    await signOutStudentAuth();
    const result = await authenticateStudent(indexNumber, password, studentRepository.findStudent);

    if (!result.ok) {
      message = result.message;
      loading = false;
      return;
    }

    saveStudentSession({
      indexNumber: result.student.index_number,
      name: result.student.name,
      accessMode: 'read-only'
    });
    try {
      const route = await getReturningStudentRoute(
        result.student.index_number,
        studentRepository.getResults,
        studentRepository.getPreferences
      );
      await goto(route);
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

      {#if password && password !== STUDENT_PASSWORD && !isAdminUsername}
        {#key turnstileVersion}
          <Turnstile onToken={(token) => { turnstileToken = token; }} />
        {/key}
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
