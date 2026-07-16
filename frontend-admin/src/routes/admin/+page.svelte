<script lang="ts">
  import { onMount } from 'svelte';
  import { api, apiMode } from '$lib/api/client';
  import type { DashboardSummary, FieldCapacity } from '$lib/types';

  let summary = $state<DashboardSummary | null>(null);
  let capacities = $state<FieldCapacity[]>([]);
  let error = $state('');

  onMount(async () => {
    try { [summary, capacities] = await Promise.all([api.getDashboard(), api.getFieldCapacities()]); }
    catch (value) { error = value instanceof Error ? value.message : 'Dashboard data could not be loaded.'; }
  });

  const percentage = (item: FieldCapacity) => Math.round((item.assigned / item.capacity) * 100);
</script>

<svelte:head><title>Overview · FieldSelect Admin</title></svelte:head>

<div class="page">
  <div class="page-header">
    <div><div class="eyebrow">Allocation control room</div><h1>Good morning, Administrator</h1><p>Here is the current state of the mock field-selection cycle.</p></div>
    <div class="header-actions"><span class="badge success">{apiMode === 'mock' ? 'Mock API healthy' : 'Backend connected'}</span><a class="button secondary" href="/admin/imports">Import data</a><a class="button primary" href="/admin/allocation">Run allocation</a></div>
  </div>

  {#if error}<div class="form-error" role="alert"><strong>!</strong> {error}</div>{/if}

  <section class="metrics" aria-label="Data summary">
    {#if summary}
      <article class="metric"><div class="metric-top"><span>Student records</span><i class="metric-icon">♙</i></div><strong>{summary.students}</strong><small>Fictional accounts in this test cycle</small></article>
      <article class="metric"><div class="metric-top"><span>Results loaded</span><i class="metric-icon">▤</i></div><strong>{summary.results}</strong><small>{summary.students - summary.results} records still missing</small></article>
      <article class="metric"><div class="metric-top"><span>Preferences</span><i class="metric-icon">✓</i></div><strong>{summary.preferences}</strong><small>{summary.students - summary.preferences} students have not submitted</small></article>
      <article class="metric"><div class="metric-top"><span>Allocated</span><i class="metric-icon">◇</i></div><strong>{summary.allocations}</strong><small>From the latest completed simulation</small></article>
      <article class="metric"><div class="metric-top"><span>Needs attention</span><i class="metric-icon attention">!</i></div><strong>{summary.validationProblems}</strong><small>Validation or allocation issues</small></article>
    {:else}
      {#each Array(5) as _}<article class="metric"><div class="skeleton" style="width:70%;height:12px"></div><div class="skeleton" style="width:45%;height:34px;margin-top:22px"></div><div class="skeleton" style="width:85%;height:9px;margin-top:12px"></div></article>{/each}
    {/if}
  </section>

  <div class="grid-2">
    <section class="panel">
      <div class="panel-head"><div><h2>Field capacity</h2><p>Seat use from the latest mock allocation</p></div><span class="badge info">{capacities.reduce((sum, item) => sum + item.assigned, 0)} assigned</span></div>
      <div class="field-list">
        {#if capacities.length}
          {#each capacities as item}
            <div class="field-row"><div class="field-name"><span>{item.shortName}</span><div>{item.name}</div></div><div class="progress" aria-label={`${item.assigned} of ${item.capacity} seats filled`}><span style={`width:${percentage(item)}%`}></span></div><div class="field-count"><strong>{item.assigned}</strong> / {item.capacity}</div></div>
          {/each}
        {:else}
          {#each Array(8) as _}<div class="field-row"><div class="skeleton" style="height:32px"></div><div class="skeleton" style="height:7px"></div><div class="skeleton" style="height:11px"></div></div>{/each}
        {/if}
      </div>
    </section>

    <section class="panel">
      <div class="panel-head"><div><h2>Recent operations</h2><p>Latest requests and data events</p></div><a class="text-link" href="/admin/api-log">API log →</a></div>
      <div class="activity-list">
        {#if summary}
          {#each summary.recentOperations as operation}
            <div class="activity"><span class:warning={operation.status === 'warning'} class:error={operation.status === 'error'} class="activity-icon">{operation.status === 'success' ? '✓' : '!'}</span><div><strong>{operation.label}</strong><p>{operation.detail}</p><small>{operation.occurredAt}</small></div></div>
          {/each}
        {:else}
          {#each Array(4) as _}<div class="activity"><div class="skeleton" style="width:29px;height:29px;border-radius:50%"></div><div><div class="skeleton" style="width:75%;height:10px"></div><div class="skeleton" style="width:92%;height:8px;margin-top:9px"></div></div></div>{/each}
        {/if}
      </div>
    </section>
  </div>
</div>

<style>
  .metric-icon.attention { background: var(--amber-soft); color: var(--amber); }
  .text-link { color: var(--blue); font-size: .69rem; font-weight: 700; text-decoration: none; white-space: nowrap; }
</style>
