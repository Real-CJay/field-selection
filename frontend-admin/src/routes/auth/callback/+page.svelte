<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import type { Session } from '@supabase/supabase-js';
  import { saveStudentSession } from '$lib/session';
  import { getAuthenticatedStudent } from '$lib/student-auth-client';
  import { markPasswordSetup } from '$lib/student-auth-state';
  import { supabase } from '$lib/supabase';

  let message = $state('Confirming your email…');
  let errorMessage = $state('');

  async function waitForSession(): Promise<Session | null> {
    const current = await supabase.auth.getSession();
    if (current.data.session) return current.data.session;
    return await new Promise((resolve) => {
      const timeout = window.setTimeout(() => {
        subscription.unsubscribe();
        resolve(null);
      }, 6000);
      const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
        if (!session) return;
        window.clearTimeout(timeout);
        subscription.unsubscribe();
        resolve(session);
      });
    });
  }

  onMount(async () => {
    try {
      const session = await waitForSession();
      if (!session) throw new Error('The confirmation link is invalid or has expired.');
      const student = await getAuthenticatedStudent(session.access_token);
      saveStudentSession({
        indexNumber: student.index_number,
        name: student.name,
        accessMode: 'read-only'
      });
      markPasswordSetup(student.index_number);
      message = 'Email confirmed. Opening password setup…';
      await goto('/preferences?password-setup=1', { replaceState: true });
    } catch (error) {
      await supabase.auth.signOut();
      errorMessage = error instanceof Error ? error.message : 'Unable to confirm this email.';
      message = '';
    }
  });
</script>

<svelte:head><title>Confirm Email · Field Selection</title></svelte:head>

<main class="callback-page">
  <section class="card callback-card">
    <h1>Email confirmation</h1>
    {#if message}<p class="muted" role="status">{message}</p>{/if}
    {#if errorMessage}
      <div class="message" role="alert">{errorMessage}</div>
      <a class="button" href="/login">Return to login</a>
    {/if}
  </section>
</main>

<style>
  .callback-page { display: grid; min-height: 100vh; place-items: center; padding: 20px; }
  .callback-card { width: min(100%, 480px); text-align: center; }
  .callback-card .button { display: inline-flex; margin-top: 18px; text-decoration: none; }
</style>
