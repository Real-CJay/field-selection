<script lang="ts">
  import { getCorrectionRequests, reviewCorrectionRequest } from '$lib/correction-client';
  import { getGradeFromGpa } from '$lib/module-grades';
  import type { GradeCorrectionRequest } from '$lib/types';

  const moduleNames = {
    cse: 'CSE',
    maths: 'Mathematics',
    electrical: 'Electrical',
    material: 'Material Science'
  };

  let username = $state('');
  let password = $state('');
  let requests = $state<GradeCorrectionRequest[]>([]);
  let authenticated = $state(false);
  let loading = $state(false);
  let message = $state('');

  async function login(event: SubmitEvent) {
    event.preventDefault();
    loading = true;
    message = '';
    try {
      requests = await getCorrectionRequests(username, password);
      authenticated = true;
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to sign in.';
    } finally {
      loading = false;
    }
  }

  async function review(id: number, decision: 'approved' | 'rejected') {
    loading = true;
    message = '';
    try {
      await reviewCorrectionRequest(id, decision, username, password);
      requests = await getCorrectionRequests(username, password);
      message = `Request ${decision}.`;
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to review the request.';
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head><title>Admin · Grade Corrections</title></svelte:head>

<main class="page">
  <h1>Grade Correction Admin</h1>
  {#if !authenticated}
    <section class="card login-card">
      <form onsubmit={login}>
        <div class="field"><label for="admin-user">Username</label><input class="input" id="admin-user" bind:value={username} required /></div>
        <div class="field"><label for="admin-password">Password</label><input class="input" id="admin-password" type="password" bind:value={password} required /></div>
        <button class="button" type="submit" disabled={loading}>{loading ? 'Signing in…' : 'Sign in'}</button>
      </form>
    </section>
  {:else}
    <section class="card">
      <h2>Correction requests</h2>
      {#if requests.length === 0}<p>No correction requests yet.</p>{/if}
      <div class="request-list">
        {#each requests as request}
          <article class="request">
            <div>
              <strong>{request.index_number} · {moduleNames[request.module]}</strong>
              <p>{getGradeFromGpa(request.current_grade)} → {request.requested_grade}</p>
              <small>{new Date(request.created_at).toLocaleString()} · {request.status}</small>
            </div>
            {#if request.status === 'pending'}
              <div class="review-actions">
                <button class="button" disabled={loading} onclick={() => review(request.id, 'approved')}>Approve</button>
                <button class="button secondary" disabled={loading} onclick={() => review(request.id, 'rejected')}>Reject</button>
              </div>
            {/if}
          </article>
        {/each}
      </div>
    </section>
  {/if}
  {#if message}<p class="message" role="status">{message}</p>{/if}
</main>

<style>
  h1 { margin-bottom: 20px; }
  .login-card { max-width: 440px; }
  .login-card .button { margin-top: 20px; }
  .request-list { display: grid; gap: 12px; margin-top: 18px; }
  .request { display: flex; align-items: center; justify-content: space-between; gap: 20px; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
  .request p { margin: 5px 0; }
  .request small { color: #6b7280; }
  .review-actions { display: flex; gap: 8px; }
  @media (max-width: 600px) { .request { align-items: stretch; flex-direction: column; } .review-actions .button { flex: 1; } }
</style>
