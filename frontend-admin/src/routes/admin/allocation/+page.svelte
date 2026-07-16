<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api/client';
  import type { AllocationRun, FieldCapacity, ReadinessCheck } from '$lib/types';

  let checks = $state<ReadinessCheck[]>([]);
  let fields = $state<FieldCapacity[]>([]);
  let run = $state<AllocationRun | null>(null);
  let loading = $state(true);
  let running = $state(false);
  let showConfirm = $state(false);
  let error = $state('');
  let toast = $state('');

  onMount(async () => {
    try { [checks, fields, run] = await Promise.all([api.getReadiness(), api.getFieldCapacities(), api.getAllocationStatus()]); }
    catch (value) { error = value instanceof Error ? value.message : 'Allocation readiness could not be loaded.'; }
    finally { loading = false; }
  });

  async function execute() {
    showConfirm = false; running = true; error = '';
    try { run = await api.runAllocation(); toast = `Allocation ${run.runId} completed: ${run.assigned} assigned and ${run.unassigned} unassigned.`; }
    catch (value) { error = value instanceof Error ? value.message : 'The allocation run failed.'; }
    finally { running = false; }
  }

  const totalCapacity = $derived(fields.reduce((sum, item) => sum + item.capacity, 0));
</script>

<svelte:head><title>Allocation run · FieldSelect Admin</title></svelte:head>

<div class="page">
  <div class="page-header"><div><div class="eyebrow">Allocation engine</div><h1>Prepare and run allocation</h1><p>Review the mock readiness checks before starting a new simulation.</p></div><div class="header-actions"><span class="badge {running ? 'warning' : 'success'}">{running ? 'Processing' : 'Engine ready'}</span><button class="button primary" disabled={loading || running} onclick={() => (showConfirm = true)}>{running ? 'Running allocation…' : 'Run new allocation'}</button></div></div>
  {#if error}<div class="form-error" role="alert"><strong>!</strong> {error}</div>{/if}

  <div class="allocation-grid">
    <section class="panel readiness">
      <div class="panel-head"><div><h2>Data readiness</h2><p>Pre-flight checks returned by the backend adapter</p></div><span class="badge {checks.every((item) => item.ready) ? 'success' : 'warning'}">{checks.filter((item) => item.ready).length} of {checks.length} passed</span></div>
      <div class="check-list">
        {#if loading}{#each Array(4) as _}<div class="check"><div class="skeleton" style="width:34px;height:34px;border-radius:50%"></div><div><div class="skeleton" style="width:160px;height:11px"></div><div class="skeleton" style="width:230px;height:8px;margin-top:8px"></div></div></div>{/each}
        {:else}{#each checks as item}<div class="check"><span class:warning={!item.ready}>{item.ready ? '✓' : '!'}</span><div><strong>{item.label}</strong><small>{item.detail}</small></div><b class:warning={!item.ready}>{item.ready ? 'Ready' : 'Review'}</b></div>{/each}{/if}
      </div>
      <div class="notice"><span>i</span><p><strong>Backend authority</strong>The frontend does not calculate allocations. It sends a run request and presents the backend response as authoritative.</p></div>
    </section>

    <aside class="panel last-run">
      <div class="panel-head"><div><h2>Latest run</h2><p>Most recent simulation outcome</p></div></div>
      <div class="run-body">
        {#if run}
          <div class="run-status"><span class:processing={running}>{running ? '↻' : '✓'}</span><div><strong>{running ? 'Allocation in progress' : run.status === 'completed' ? 'Run completed' : run.status}</strong><small>{run.runId}</small></div></div>
          <div class="run-numbers"><div><strong>{run.assigned}</strong><span>Assigned</span></div><div><strong>{run.unassigned}</strong><span>Unassigned</span></div><div><strong>{totalCapacity}</strong><span>Total seats</span></div></div>
          {#if run.completedAt}<p class="completed">Completed {new Date(run.completedAt).toLocaleString()}</p>{/if}
          <a class="button secondary" href="/admin/results">Inspect results</a>
        {:else}<div class="empty"><div class="empty-icon">◇</div>No allocation run is available.</div>{/if}
      </div>
    </aside>
  </div>

  <section class="panel capacity">
    <div class="panel-head"><div><h2>Configured field capacities</h2><p>Capacity is displayed for verification and remains backend-controlled.</p></div><span class="badge info">{totalCapacity} total seats</span></div>
    <div class="capacity-grid">{#each fields as field}<article><span>{field.shortName}</span><div><strong>{field.name}</strong><small>{field.capacity - field.assigned} open in latest run</small></div><b>{field.capacity}</b></article>{/each}</div>
  </section>
</div>

{#if showConfirm}
  <div class="modal-backdrop" role="presentation" onclick={(event) => { if (event.target === event.currentTarget) showConfirm = false; }}>
    <dialog class="modal" open aria-labelledby="confirm-title"><span class="confirm-icon">◇</span><h2 id="confirm-title">Run a new allocation?</h2><p>This sends a simulated request using the current student records, results, preferences, and field capacities. The previous mock result will be replaced.</p><div class="modal-actions"><button class="button secondary" onclick={() => (showConfirm = false)}>Cancel</button><button class="button primary" onclick={execute}>Confirm and run</button></div></dialog>
  </div>
{/if}
{#if toast}<div class="toast" role="status"><span>✓</span>{toast}<button aria-label="Dismiss" onclick={() => (toast = '')}>×</button></div>{/if}

<style>
  .allocation-grid { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(300px, .65fr); gap: 16px; margin-bottom: 16px; }
  .check-list { padding: 8px 22px; }
  .check { display: grid; grid-template-columns: 36px 1fr auto; align-items: center; gap: 11px; padding: 13px 0; border-bottom: 1px solid #edf0f4; }
  .check > span { display: grid; width: 33px; height: 33px; place-items: center; border-radius: 50%; background: var(--green-soft); color: var(--green); font-size: .7rem; font-weight: 800; }
  .check > span.warning { background: var(--amber-soft); color: var(--amber); }
  .check strong, .check small { display: block; }
  .check strong { font-size: .75rem; }
  .check small { margin-top: 3px; color: #8994a7; font-size: .64rem; }
  .check b { color: var(--green); font-size: .61rem; }
  .check b.warning { color: var(--amber); }
  .notice { display: flex; gap: 10px; margin: 9px 22px 20px; border-radius: 10px; background: #f3f6fb; padding: 13px; }
  .notice > span { display: grid; flex: 0 0 21px; height: 21px; place-items: center; border-radius: 50%; background: #dfe7f5; color: #526b99; font-family: serif; font-weight: 800; }
  .notice p { margin: 0; color: #718098; font-size: .64rem; line-height: 1.5; }
  .notice strong { display: block; color: #4f607e; }
  .run-body { padding: 22px; }
  .run-status { display: flex; align-items: center; gap: 11px; }
  .run-status > span { display: grid; width: 39px; height: 39px; place-items: center; border-radius: 12px; background: var(--green-soft); color: var(--green); font-weight: 800; }
  .run-status > span.processing { background: var(--amber-soft); color: var(--amber); animation: spin 1s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .run-status strong, .run-status small { display: block; }
  .run-status strong { font-size: .76rem; }
  .run-status small { margin-top: 3px; color: #8b96a9; font-family: monospace; font-size: .56rem; }
  .run-numbers { display: grid; grid-template-columns: repeat(3, 1fr); gap: 7px; margin: 22px 0 14px; }
  .run-numbers div { border-radius: 9px; background: #f5f7fa; padding: 11px 8px; text-align: center; }
  .run-numbers strong, .run-numbers span { display: block; }
  .run-numbers strong { font-family: 'Manrope'; font-size: 1rem; }
  .run-numbers span { margin-top: 3px; color: #8d97a8; font-size: .55rem; }
  .completed { color: #929cad; font-size: .6rem; }
  .run-body .button { width: 100%; margin-top: 9px; }
  .capacity-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 9px; padding: 18px 22px 22px; }
  .capacity-grid article { display: grid; grid-template-columns: 34px 1fr auto; align-items: center; gap: 9px; border: 1px solid #e8ecf2; border-radius: 10px; padding: 10px; }
  .capacity-grid article > span { display: grid; height: 34px; place-items: center; border-radius: 8px; background: var(--blue-soft); color: var(--blue); font-size: .53rem; font-weight: 800; }
  .capacity-grid strong, .capacity-grid small { display: block; }
  .capacity-grid strong { overflow: hidden; max-width: 130px; font-size: .61rem; text-overflow: ellipsis; white-space: nowrap; }
  .capacity-grid small { margin-top: 3px; color: #929daf; font-size: .52rem; }
  .capacity-grid b { font-size: .72rem; }
  .confirm-icon { display: grid; width: 44px; height: 44px; margin-bottom: 16px; place-items: center; border-radius: 13px; background: var(--blue-soft); color: var(--blue); font-size: 1.2rem; }
  .toast button { margin-left: auto; border: 0; background: transparent; color: inherit; cursor: pointer; }
  @media (max-width: 1100px) { .capacity-grid { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 850px) { .allocation-grid { grid-template-columns: 1fr; } }
  @media (max-width: 520px) { .capacity-grid { grid-template-columns: 1fr; } }
</style>
