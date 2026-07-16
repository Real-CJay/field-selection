<script lang="ts">
  import { apiLogs, clearApiLogs } from '$lib/stores';
  import type { ApiLogEntry } from '$lib/types';
  let selected = $state<ApiLogEntry | null>(null);
  const formatJson = (value: unknown) => value === undefined ? 'No payload' : JSON.stringify(value, null, 2);
</script>

<svelte:head><title>API activity · FieldSelect Admin</title></svelte:head>

<div class="page">
  <div class="page-header"><div><div class="eyebrow">Integration diagnostics</div><h1>API request activity</h1><p>Inspect every simulated request, response, status code, and duration.</p></div><div class="header-actions"><span class="badge info">{$apiLogs.length} requests</span><button class="button secondary" disabled={!$apiLogs.length} onclick={() => { clearApiLogs(); selected = null; }}>Clear log</button></div></div>

  <div class="log-grid">
    <section class="panel">
      <div class="panel-head"><div><h2>Request timeline</h2><p>Newest requests appear first</p></div><span class="live"><i></i>Live</span></div>
      {#if $apiLogs.length}<div class="log-list">{#each $apiLogs as entry}<button class:active={selected?.id === entry.id} onclick={() => (selected = entry)}><span class="method {entry.method.toLowerCase()}">{entry.method}</span><div><strong>{entry.path}</strong><small>{new Date(entry.timestamp).toLocaleTimeString()}</small></div><b class:error={entry.status >= 400}>{entry.status}</b><em>{entry.duration} ms</em></button>{/each}</div>{:else}<div class="empty"><div class="empty-icon">↔</div><strong>No requests yet</strong><p>Visit the dashboard or run an import to generate mock API activity.</p></div>{/if}
    </section>

    <aside class="panel inspector">
      <div class="panel-head"><div><h2>Request inspector</h2><p>Payload and response body</p></div></div>
      {#if selected}<div class="inspect-body"><div class="inspect-meta"><div><span>Method</span><strong>{selected.method}</strong></div><div><span>Status</span><strong class:error={selected.status >= 400}>{selected.status}</strong></div><div><span>Duration</span><strong>{selected.duration} ms</strong></div></div><h3>Endpoint</h3><code class="endpoint">{selected.path}</code><h3>Request payload</h3><pre>{formatJson(selected.request)}</pre><h3>Response body</h3><pre>{formatJson(selected.response)}</pre></div>{:else}<div class="empty"><div class="empty-icon">⌕</div><strong>Select a request</strong><p>Choose an entry to view its complete exchange.</p></div>{/if}
    </aside>
  </div>
</div>

<style>
  .log-grid { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(340px, .85fr); gap: 16px; align-items: start; }
  .live { display: flex; align-items: center; gap: 6px; color: var(--green); font-size: .61rem; font-weight: 700; }
  .live i { width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 4px var(--green-soft); }
  .log-list { max-height: 660px; overflow-y: auto; padding: 8px; }
  .log-list button { display: grid; grid-template-columns: 47px 1fr 42px 65px; align-items: center; gap: 10px; width: 100%; border: 1px solid transparent; border-radius: 9px; background: transparent; padding: 10px; color: #55627a; cursor: pointer; text-align: left; }
  .log-list button:hover, .log-list button.active { border-color: #dce5f6; background: #f5f8fe; }
  .method { border-radius: 5px; background: var(--green-soft); padding: 4px 5px; color: var(--green); font-family: monospace; font-size: .56rem; font-weight: 800; text-align: center; }
  .method.post { background: var(--blue-soft); color: var(--blue); }
  .log-list strong, .log-list small { display: block; }
  .log-list strong { overflow: hidden; color: var(--navy); font-family: monospace; font-size: .65rem; text-overflow: ellipsis; white-space: nowrap; }
  .log-list small { margin-top: 3px; color: #919bad; font-size: .55rem; }
  .log-list b { color: var(--green); font-size: .65rem; }
  .log-list b.error, .inspect-meta strong.error { color: var(--red); }
  .log-list em { color: #8590a4; font-size: .57rem; font-style: normal; text-align: right; }
  .inspector { position: sticky; top: 84px; }
  .inspect-body { padding: 19px 22px 24px; }
  .inspect-meta { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .inspect-meta div { border-radius: 8px; background: #f5f7fa; padding: 9px; }
  .inspect-meta span, .inspect-meta strong { display: block; }
  .inspect-meta span { color: #8a95a8; font-size: .52rem; }
  .inspect-meta strong { margin-top: 3px; font-size: .67rem; }
  .inspect-body h3 { margin: 18px 0 7px; font-size: .66rem; }
  .endpoint { display: block; overflow-x: auto; border-radius: 7px; background: #edf3ff; padding: 9px; color: #315cae; font-size: .62rem; }
  pre { overflow: auto; max-height: 230px; margin: 0; border-radius: 8px; background: #17243e; padding: 13px; color: #c3d2ee; font-size: .58rem; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
  @media (max-width: 980px) { .log-grid { grid-template-columns: 1fr; } .inspector { position: static; } }
  @media (max-width: 520px) { .log-list button { grid-template-columns: 44px 1fr 38px; } .log-list em { display: none; } }
</style>
