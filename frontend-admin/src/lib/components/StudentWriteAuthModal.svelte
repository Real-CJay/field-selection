<script lang="ts">
  import Turnstile from './Turnstile.svelte';
  import { requestStudentMagicLink } from '$lib/student-auth-client';
  import { isMaintenancePreviewStudent } from '$lib/maintenance-access';
  import { clearPasswordSetup, markPasswordSetup } from '$lib/student-auth-state';
  import { saveStudentSession, getStudentSession } from '$lib/session';
  import { supabase } from '$lib/supabase';

  type Mode = 'notice' | 'magic-link-sent' | 'password';

  let {
    open,
    indexNumber,
    initialMode = 'notice',
    onAuthenticated,
    onCancel,
    onLogout
  }: {
    open: boolean;
    indexNumber: string;
    initialMode?: Mode;
    onAuthenticated: () => void | Promise<void>;
    onCancel: () => void;
    onLogout: () => void | Promise<void>;
  } = $props();

  let mode = $state<Mode>('notice');
  let personalPassword = $state('');
  let passwordConfirmation = $state('');
  let turnstileToken = $state('');
  let turnstileVersion = $state(0);
  let message = $state('');
  let busy = $state(false);
  let wasOpen = false;
  let canTestStudentWrites = $derived(isMaintenancePreviewStudent(indexNumber));

  $effect(() => {
    if (open && !wasOpen) {
      mode = initialMode;
      personalPassword = '';
      passwordConfirmation = '';
      turnstileToken = '';
      message = '';
    }
    wasOpen = open;
  });

  async function sendMagicLink() {
    if (!isMaintenancePreviewStudent(indexNumber)) {
      message = 'Editing is currently under work. Please try again later.';
      return;
    }
    if (!turnstileToken) {
      message = 'Complete the security check first.';
      return;
    }
    busy = true;
    message = '';
    try {
      message = await requestStudentMagicLink(indexNumber, turnstileToken);
      markPasswordSetup(indexNumber);
      mode = 'magic-link-sent';
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to send the confirmation email.';
      turnstileToken = '';
      turnstileVersion += 1;
    } finally {
      busy = false;
    }
  }

  async function createPassword() {
    if (personalPassword.length < 8) {
      message = 'Use at least 8 characters for your personal password.';
      return;
    }
    if (personalPassword !== passwordConfirmation) {
      message = 'The passwords do not match.';
      return;
    }
    busy = true;
    message = '';
    const { error } = await supabase.auth.updateUser({ password: personalPassword });
    if (error) {
      message = 'Unable to create your personal password. Please try again.';
      busy = false;
      return;
    }
    const session = getStudentSession();
    if (session) saveStudentSession({ ...session, accessMode: 'editable' });
    clearPasswordSetup();
    busy = false;
    await onAuthenticated();
  }
</script>

{#if open}
  <div class="modal-backdrop" role="presentation">
    <div class="card auth-modal" role="dialog" aria-modal="true" aria-labelledby="edit-auth-heading">
      {#if !canTestStudentWrites}
        <h2 id="edit-auth-heading">Editing is currently under work</h2>
        <p class="muted">Changes cannot be saved yet. Please try again later.</p>
      {:else}
        <h2 id="edit-auth-heading">Verify before saving</h2>
      {/if}
      {#if canTestStudentWrites && mode === 'notice'}
        <p class="muted">
          You are signed in with the read-only password. To make changes, log out and sign in with your personal password.
        </p>
        <button class="button auth-action" type="button" onclick={onLogout}>Log out and sign in</button>
        <p class="muted forgot-copy">Don’t have a personal password or forgot it?</p>
        {#key turnstileVersion}
          <Turnstile onToken={(token) => { turnstileToken = token; }} />
        {/key}
        <button class="button secondary auth-action" type="button" onclick={sendMagicLink} disabled={busy}>
          {busy ? 'Sending confirmation email…' : 'Send confirmation email'}
        </button>
      {:else if canTestStudentWrites && mode === 'magic-link-sent'}
        <p class="muted">{message}</p>
        <p class="muted">Open the confirmation link in that email to continue.</p>
      {:else if canTestStudentWrites}
        <p class="muted">Your email has been verified. Create a new personal password for future changes.</p>
        <div class="field">
          <label for="personal-password">Personal password</label>
          <input class="input" id="personal-password" type="password" bind:value={personalPassword} autocomplete="new-password" />
        </div>
        <div class="field">
          <label for="personal-password-confirmation">Confirm personal password</label>
          <input class="input" id="personal-password-confirmation" type="password" bind:value={passwordConfirmation} autocomplete="new-password" />
        </div>
        <p class="remember-password">Please remember this password. You will need it whenever you want to make changes.</p>
        <button class="button auth-action" type="button" onclick={createPassword} disabled={busy}>
          {busy ? 'Creating password…' : 'Create personal password'}
        </button>
      {/if}
      {#if canTestStudentWrites && message && mode !== 'magic-link-sent'}<div class="message" role="alert">{message}</div>{/if}
      <button class="button secondary cancel-auth" type="button" onclick={onCancel} disabled={busy}>Cancel</button>
    </div>
  </div>
{/if}

<style>
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
  .forgot-copy { margin: 18px 0 0; }
  .remember-password { margin: 18px 0 0; color: #374151; font-size: 0.9rem; }
</style>
