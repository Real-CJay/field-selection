<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { api, apiMode } from '$lib/api/client';
  import { saveSession, session } from '$lib/stores';

  let email = $state('admin@fieldselect.test');
  let password = $state('admin123');
  let loading = $state(false);
  let message = $state('');
  let showPassword = $state(false);

  onMount(() => { if ($session) goto('/admin', { replaceState: true }); });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    message = '';
    try {
      const value = await api.login(email, password);
      saveSession(value);
      await goto('/admin');
    } catch (error) {
      message = error instanceof Error ? error.message : 'Login failed. Please try again.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Admin sign in · FieldSelect</title></svelte:head>

<main class="login-page">
  <section class="login-card">
      <div class="brand"><span>FS</span><div><strong>FieldSelect</strong><small>Admin console</small></div></div>
      <h1>Admin login</h1>
      <p class="intro">Enter the demo credentials to continue.</p>

      <form onsubmit={submit}>
        <label class="form-label" for="email">Email address</label>
        <input class="input" id="email" type="email" bind:value={email} autocomplete="username" required />

        <div class="password-label"><label class="form-label" for="password">Password</label><span>Mock access</span></div>
        <div class="password-input">
          <input class="input" id="password" type={showPassword ? 'text' : 'password'} bind:value={password} autocomplete="current-password" required />
          <button type="button" onclick={() => (showPassword = !showPassword)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? 'Hide' : 'Show'}</button>
        </div>

        {#if message}<div class="form-error" role="alert"><strong>!</strong> {message}</div>{/if}

        <button class="button primary submit" type="submit" disabled={loading}>
          {loading ? 'Checking credentials…' : 'Sign in to console'}
        </button>
      </form>

      <div class="demo-box"><span>Demo credentials</span><code>admin@fieldselect.test</code><code>admin123</code></div>
      <p class="mode">Mode: <strong>{apiMode}</strong></p>
  </section>
</main>

<style>
  .login-page { display: grid; min-height: 100vh; place-items: center; background: #f4f6fa; padding: 24px; }
  .login-card { width: min(420px, 100%); border: 1px solid var(--line); border-radius: 14px; background: #fff; padding: 32px; box-shadow: 0 8px 24px rgba(23, 36, 62, .08); }
  .brand { display: flex; align-items: center; gap: 11px; margin-bottom: 32px; color: var(--navy); font-family: 'Manrope'; }
  .brand > span { display: grid; width: 41px; height: 41px; place-items: center; border-radius: 10px; background: var(--navy); color: #fff; font-size: .7rem; font-weight: 800; }
  .brand strong, .brand small { display: block; }
  .brand strong { font-size: .92rem; }
  .brand small { margin-top: 2px; color: #8994a7; font-family: 'DM Sans'; font-size: .58rem; font-weight: 600; text-transform: uppercase; }
  .login-card h1 { margin-bottom: 7px; font-size: 1.5rem; letter-spacing: -.035em; }
  .intro { margin-bottom: 32px; color: var(--ink-muted); font-size: .85rem; }
  form > .form-label { margin-top: 19px; }
  .password-label { display: flex; align-items: center; justify-content: space-between; margin-top: 19px; }
  .password-label .form-label { margin: 0; }
  .password-label span { color: #929bad; font-size: .62rem; }
  .password-input { position: relative; }
  .password-input .input { padding-right: 60px; }
  .password-input button { position: absolute; top: 0; right: 4px; height: 42px; border: 0; background: transparent; color: var(--blue); cursor: pointer; font-size: .65rem; font-weight: 700; }
  .submit { width: 100%; margin-top: 25px; }
  .demo-box { display: grid; grid-template-columns: 1fr auto; gap: 5px 16px; margin-top: 22px; border-radius: 11px; background: #f5f7fb; padding: 13px 15px; color: #7b879c; font-size: .64rem; }
  .demo-box span { grid-row: 1 / 3; align-self: center; font-weight: 700; }
  .demo-box code { color: #42516d; font-size: .65rem; }
  .mode { margin: 19px 0 0; color: #9aa3b2; font-size: .62rem; text-align: center; }
  @media (max-width: 480px) { .login-page { padding: 14px; } .login-card { padding: 24px 20px; } }
</style>
