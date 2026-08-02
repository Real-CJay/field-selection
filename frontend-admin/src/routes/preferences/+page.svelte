<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import {
    DEPARTMENTS,
    emptyRankings,
    preferencesToRankings,
    rankingsToPreferences,
    validateRankings
  } from '$lib/preferences';
  import { hasSubmittedModuleGrades } from '$lib/module-grades';
  import {
    clearStudentSession,
    getModuleGrades,
    getStudentSession,
    saveStudentSession
  } from '$lib/session';
  import { studentRepository } from '$lib/student-repository';
  import {
    hasEditableSession,
    sendPreferenceOtp,
    signOutStudentAuth,
    verifyPreferenceOtp
  } from '$lib/student-edit-auth';
  import { POST_PREFERENCES_ROUTE } from '$lib/navigation';
  import type { StudentRankings, StudentSession } from '$lib/types';

  const rankOptions = Array.from({ length: DEPARTMENTS.length }, (_, index) => index + 1);

  let session = $state<StudentSession | null>(null);
  let rankings = $state<StudentRankings>(emptyRankings());
  let loading = $state(true);
  let saving = $state(false);
  let errorMessage = $state('');
  let showAuthentication = $state(false);
  let authMode = $state<'notice' | 'otp' | 'password'>('notice');
  let otp = $state('');
  let personalPassword = $state('');
  let passwordConfirmation = $state('');
  let authMessage = $state('');
  let authenticating = $state(false);

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

  async function savePreferences() {
    if (!session) return;
    saving = true;
    try {
      await studentRepository.savePreferences(rankingsToPreferences(session.indexNumber, rankings));
      await goto(POST_PREFERENCES_ROUTE);
    } catch {
      errorMessage = 'Unable to save preferences. Please try again.';
    } finally {
      saving = false;
    }
  }

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    if (!session) return;

    errorMessage = validateRankings(rankings) ?? '';
    if (errorMessage) return;

    if (await hasEditableSession(session.indexNumber, studentRepository.findStudentEmail)) {
      await savePreferences();
      return;
    }

    showAuthentication = true;
    authMode = 'notice';
    authMessage = '';
    personalPassword = '';
    passwordConfirmation = '';
    otp = '';
  }

  async function sendOtp() {
    if (!session) return;
    authenticating = true;
    authMessage = '';
    const result = await sendPreferenceOtp(session.indexNumber, studentRepository.findStudentEmail);
    authenticating = false;
    if (!result.ok) {
      authMessage = result.message;
      return;
    }
    authMode = 'otp';
  }

  async function verifyOtp() {
    if (!/^[0-9]{6}$/.test(otp)) {
      authMessage = 'Enter the six-digit code from your email.';
      return;
    }
    if (!session) return;
    authenticating = true;
    authMessage = '';
    const result = await verifyPreferenceOtp(
      session.indexNumber,
      otp,
      studentRepository.findStudentEmail
    );
    authenticating = false;
    if (!result.ok) {
      authMessage = result.message;
      return;
    }
    authMode = 'password';
  }

  async function createPassword() {
    if (!session) return;
    if (personalPassword.length < 8) {
      authMessage = 'Use at least 8 characters for your personal password.';
      return;
    }
    if (personalPassword !== passwordConfirmation) {
      authMessage = 'The passwords do not match.';
      return;
    }
    authenticating = true;
    authMessage = '';
    // The verified OTP already established the session. Update only the password here.
    const { supabase } = await import('$lib/supabase');
    const { error } = await supabase.auth.updateUser({ password: personalPassword });
    authenticating = false;
    if (error) {
      authMessage = 'Unable to create your personal password. Please try again.';
      return;
    }
    session = { ...session, accessMode: 'editable' };
    saveStudentSession(session);
    showAuthentication = false;
    await savePreferences();
  }

  async function logout() {
    clearStudentSession();
    await signOutStudentAuth();
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
        <button class="button save" type="submit" disabled={saving}>
          {saving ? 'Saving…' : 'Save Preferences'}
        </button>
      </form>
    {/if}
  </section>

  {#if showAuthentication}
    <div class="modal-backdrop" role="presentation">
      <div class="card auth-modal" role="dialog" aria-modal="true" aria-labelledby="edit-auth-heading">
        <h2 id="edit-auth-heading">Verify before saving</h2>
        {#if authMode === 'notice'}
          <p class="muted">
            You are signed in with the read-only password. To edit your preferences, log out and sign in with your personal password.
          </p>
          <button class="button auth-action" type="button" onclick={logout}>
            Log out and sign in
          </button>
          <button class="button secondary auth-action" type="button" onclick={sendOtp} disabled={authenticating}>
            {authenticating ? 'Sending code…' : 'Don’t have a personal password or forgot it?'}
          </button>
        {:else if authMode === 'otp'}
          <p class="muted">A one-time code was sent to the email address registered for this index number.</p>
          <div class="field">
            <label for="otp">Six-digit verification code</label>
            <input class="input" id="otp" bind:value={otp} inputmode="numeric" autocomplete="one-time-code" maxlength="6" />
          </div>
          <button class="button auth-action" type="button" onclick={verifyOtp} disabled={authenticating}>
            {authenticating ? 'Verifying…' : 'Verify code'}
          </button>
        {:else if authMode === 'password'}
          <p class="muted">Your email has been verified. Create a new personal password for future preference changes.</p>
          <div class="field">
            <label for="personal-password">Personal password</label>
            <input class="input" id="personal-password" type="password" bind:value={personalPassword} autocomplete="new-password" />
          </div>
          <div class="field">
            <label for="personal-password-confirmation">Confirm personal password</label>
            <input class="input" id="personal-password-confirmation" type="password" bind:value={passwordConfirmation} autocomplete="new-password" />
          </div>
          <p class="remember-password">Please remember this password. You will need it whenever you want to change your preferences.</p>
          <button class="button auth-action" type="button" onclick={createPassword} disabled={authenticating}>
            {authenticating ? 'Creating password…' : 'Create password and save preferences'}
          </button>
        {/if}
        {#if authMessage}<div class="message" role="alert">{authMessage}</div>{/if}
        <button class="button secondary cancel-auth" type="button" onclick={() => { showAuthentication = false; authMessage = ''; }} disabled={authenticating}>Cancel</button>
      </div>
    </div>
  {/if}

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

  .modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 20;
    display: grid;
    place-items: center;
    padding: 20px;
    background: rgb(15 23 42 / 58%);
  }

  .auth-modal { width: min(100%, 460px); }
  .auth-action, .cancel-auth { width: 100%; margin-top: 14px; }
  .remember-password { margin: 18px 0 0; color: #374151; font-size: 0.9rem; }

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
