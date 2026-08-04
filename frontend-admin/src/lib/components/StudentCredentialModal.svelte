<script lang="ts">
  import {
    createStudentPassword,
    signInStudent,
    tokenFromLogin,
    verifyRecoveryCode
  } from '$lib/student-auth-client';
  import { saveStudentApiSession } from '$lib/student-api-session';
  import { getStudentSession, saveStudentSession } from '$lib/session';

  type Mode = 'options' | 'password' | 'recovery' | 'create';

  let {
    open,
    indexNumber,
    initialMode = 'options',
    hasPersonalPassword = true,
    onAuthenticated,
    onCancel
  }: {
    open: boolean;
    indexNumber: string;
    initialMode?: Mode;
    hasPersonalPassword?: boolean;
    onAuthenticated: () => void | Promise<void>;
    onCancel: () => void;
  } = $props();

  let mode = $state<Mode>('options');
  let displayMode = $derived<Mode>(
    mode === 'options'
      ? (initialMode === 'options' && !hasPersonalPassword ? 'recovery' : initialMode)
      : mode
  );
  let personalPassword = $state('');
  let passwordConfirmation = $state('');
  let recoveryCode = $state('');
  let setupToken = $state('');
  let message = $state('');
  let busy = $state(false);
  let wasOpen = false;

  $effect(() => {
    if (open && !wasOpen) {
      mode = initialMode === 'options' && !hasPersonalPassword ? 'recovery' : initialMode;
      personalPassword = '';
      passwordConfirmation = '';
      recoveryCode = '';
      setupToken = '';
      message = '';
    }
    wasOpen = open;
  });

  function installEditableSession(result: Awaited<ReturnType<typeof signInStudent>>) {
    if (result.access_mode !== 'editable') {
      throw new Error('Enter your personal password, not the shared read-only password.');
    }
    const current = getStudentSession();
    if (current && current.indexNumber !== result.index_number) {
      throw new Error('The authenticated student does not match this page.');
    }
    saveStudentApiSession({ accessMode: 'editable', token: tokenFromLogin(result) });
    saveStudentSession({
      indexNumber: result.index_number,
      name: result.name,
      accessMode: 'editable'
    });
  }

  async function usePersonalPassword() {
    busy = true;
    message = '';
    try {
      const result = await signInStudent(indexNumber, personalPassword);
      installEditableSession(result);
      await onAuthenticated();
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to authenticate.';
    } finally {
      busy = false;
    }
  }

  async function verifyCode() {
    busy = true;
    message = '';
    try {
      const challenge = await verifyRecoveryCode(indexNumber, recoveryCode);
      setupToken = challenge.password_setup_token;
      personalPassword = '';
      passwordConfirmation = '';
      mode = 'create';
    } catch (error) {
      message = error instanceof Error ? error.message : 'Invalid recovery code.';
    } finally {
      busy = false;
    }
  }

  async function createPassword() {
    busy = true;
    message = '';
    try {
      const result = await createStudentPassword(
        setupToken,
        personalPassword,
        passwordConfirmation
      );
      installEditableSession(result);
      await onAuthenticated();
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to create the password.';
    } finally {
      busy = false;
    }
  }
</script>

{#if open}
  <div class="modal-backdrop" role="presentation">
    <div class="card auth-modal" role="dialog" aria-modal="true" aria-labelledby="student-auth-heading">
      <h2 id="student-auth-heading">
        {displayMode === 'create' ? 'Create your personal password' : 'Verify before saving'}
      </h2>

      {#if displayMode === 'options'}
        <p class="muted">Use your personal password, or use your 16-digit recovery code to reset it.</p>
        {#if hasPersonalPassword}
          <button class="button auth-action" type="button" onclick={() => { mode = 'password'; message = ''; }}>
            Use personal password
          </button>
        {/if}
        <button class="button secondary auth-action" type="button" onclick={() => { mode = 'recovery'; message = ''; }}>
          Use/reset with 16-digit code
        </button>
      {:else if displayMode === 'password'}
        <div class="field">
          <label for="modal-personal-password">Personal password</label>
          <input class="input" id="modal-personal-password" type="password" bind:value={personalPassword} autocomplete="current-password" />
        </div>
        <button class="button auth-action" type="button" onclick={usePersonalPassword} disabled={busy || !personalPassword}>
          {busy ? 'Checking…' : 'Continue and save'}
        </button>
        <button class="link-button" type="button" onclick={() => { mode = 'recovery'; message = ''; }}>
          Forgot your personal password?
        </button>
      {:else if displayMode === 'recovery'}
        <p class="muted">
          {hasPersonalPassword
            ? 'Enter your permanent 16-digit recovery code to reset your personal password.'
            : 'Enter the permanent 16-digit recovery code provided to you to create your personal password.'}
        </p>
        <p class="recovery-help">
          If you do not have access to your recovery code, please ask your E-Group representative for it.
        </p>
        <div class="field">
          <label for="student-recovery-code">Recovery code</label>
          <input class="input" id="student-recovery-code" bind:value={recoveryCode} inputmode="numeric" autocomplete="one-time-code" placeholder="1234-5678-9012-3456" />
        </div>
        <button class="button auth-action" type="button" onclick={verifyCode} disabled={busy || !recoveryCode}>
          {busy ? 'Verifying…' : 'Verify recovery code'}
        </button>
      {:else}
        <p class="muted">Choose a personal password with at least 6 characters. It cannot be <code>student123</code>.</p>
        <div class="field">
          <label for="new-personal-password">Personal password</label>
          <input class="input" id="new-personal-password" type="password" bind:value={personalPassword} autocomplete="new-password" />
        </div>
        <div class="field">
          <label for="new-personal-password-confirmation">Confirm personal password</label>
          <input class="input" id="new-personal-password-confirmation" type="password" bind:value={passwordConfirmation} autocomplete="new-password" />
        </div>
        <p class="remember">Please remember this password. You will need it whenever you want to make changes.</p>
        <button class="button auth-action" type="button" onclick={createPassword} disabled={busy || !personalPassword || !passwordConfirmation}>
          {busy ? 'Creating…' : 'Create password and continue'}
        </button>
      {/if}

      {#if message}<div class="message" role="alert">{message}</div>{/if}
      <button class="button secondary cancel" type="button" onclick={onCancel} disabled={busy}>Cancel</button>
    </div>
  </div>
{/if}

<style>
  .modal-backdrop { position: fixed; inset: 0; z-index: 30; display: grid; place-items: center; padding: 20px; background: rgb(15 23 42 / 58%); }
  .auth-modal { width: min(100%, 470px); }
  .auth-action, .cancel { width: 100%; margin-top: 14px; }
  .field { margin-top: 16px; }
  .recovery-help { margin: 16px 0 0; padding: 14px 16px; border: 2px solid #d97706; border-radius: 8px; background: #fffbeb; color: #78350f; font-size: 1rem; font-weight: 700; line-height: 1.45; }
  .remember { color: #374151; font-size: 0.9rem; }
  .link-button { width: 100%; margin-top: 14px; border: 0; background: transparent; color: #1d4ed8; cursor: pointer; text-decoration: underline; }
  code { font-size: 0.9em; }
</style>
