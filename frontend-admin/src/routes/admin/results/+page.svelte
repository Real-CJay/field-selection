<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api/client';
  import type { Allocation, FieldCapacity } from '$lib/types';

  let results = $state<Allocation[]>([]);
  let fields = $state<FieldCapacity[]>([]);
  let search = $state('');
  let field = $state('all');
  let status = $state<'all' | 'assigned' | 'unassigned'>('all');
  let sort = $state<'sgpa-desc' | 'sgpa-asc' | 'name'>('sgpa-desc');
  let pageNumber = $state(1);
  let loading = $state(true);
  let error = $state('');
  let selected = $state<Allocation | null>(null);
  const pageSize = 10;

  onMount(async () => {
    try { [results, fields] = await Promise.all([api.getResults(), api.getFieldCapacities()]); }
    catch (value) { error = value instanceof Error ? value.message : 'Allocation results could not be loaded.'; }
    finally { loading = false; }
  });

  let filtered = $derived(results.filter((item) => {
    const query = search.toLowerCase().trim();
    return (!query || item.student.name.toLowerCase().includes(query) || item.student.indexNumber.toLowerCase().includes(query)) && (field === 'all' || item.assignedField === field) && (status === 'all' || item.status === status);
  }).sort((a, b) => sort === 'name' ? a.student.name.localeCompare(b.student.name) : sort === 'sgpa-asc' ? a.sgpa - b.sgpa : b.sgpa - a.sgpa));
  let totalPages = $derived(Math.max(1, Math.ceil(filtered.length / pageSize)));
  let pageRows = $derived(filtered.slice((Math.min(pageNumber, totalPages) - 1) * pageSize, Math.min(pageNumber, totalPages) * pageSize));

  function resetPage() { pageNumber = 1; }
  function label(id: string | null) { return fields.find((item) => item.id === id)?.name ?? 'Not assigned'; }
  function exportCsv() {
    const headers = ['Index Number', 'Name', 'SGPA', 'Status', 'Assigned Field', 'Preference Rank', 'Reason'];
    const rows = filtered.map((item) => [item.student.indexNumber, item.student.name, item.sgpa, item.status, label(item.assignedField), item.preferenceRank ?? '', item.reason ?? '']);
    const csv = [headers, ...rows].map((row) => row.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(',')).join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' })); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'mock-allocation-results.csv'; anchor.click(); URL.revokeObjectURL(url);
  }
</script>

<svelte:head><title>Allocation results · FieldSelect Admin</title></svelte:head>

<div class="page">
  <div class="page-header"><div><div class="eyebrow">Allocation audit</div><h1>Review allocation results</h1><p>Search, filter, inspect, and export the latest backend response.</p></div><div class="header-actions"><span class="badge success">{results.filter((item) => item.status === 'assigned').length} assigned</span><button class="button secondary" disabled={!filtered.length} onclick={exportCsv}>↓ Export CSV</button></div></div>
  {#if error}<div class="form-error" role="alert"><strong>!</strong> {error}</div>{/if}

  <section class="panel">
    <div class="panel-head result-head"><div><h2>Student outcomes</h2><p>{filtered.length} of {results.length} fictional records shown</p></div><div class="toolbar"><input class="input" aria-label="Search students" placeholder="Search name or index…" bind:value={search} oninput={resetPage} /><select class="select" aria-label="Filter by field" bind:value={field} onchange={resetPage}><option value="all">All fields</option>{#each fields as item}<option value={item.id}>{item.shortName} · {item.name}</option>{/each}</select><select class="select" aria-label="Filter by status" bind:value={status} onchange={resetPage}><option value="all">All statuses</option><option value="assigned">Assigned</option><option value="unassigned">Unassigned</option></select><select class="select" aria-label="Sort results" bind:value={sort}><option value="sgpa-desc">SGPA: high to low</option><option value="sgpa-asc">SGPA: low to high</option><option value="name">Name: A to Z</option></select></div></div>
    <div class="table-wrap">
      {#if loading}<div class="empty"><div class="skeleton" style="height:220px"></div></div>
      {:else if pageRows.length}
        <table><thead><tr><th>Student</th><th>Index number</th><th>SGPA</th><th>Status</th><th>Assigned field</th><th>Choice</th><th></th></tr></thead><tbody>{#each pageRows as item}<tr><td><div class="student-cell"><span class="avatar">{item.student.name.split(' ').map((part) => part[0]).join('').slice(0,2)}</span><div><strong>{item.student.name}</strong><small>{item.student.email}</small></div></div></td><td><strong>{item.student.indexNumber}</strong></td><td><span class="sgpa">{item.sgpa.toFixed(2)}</span></td><td><span class="badge {item.status === 'assigned' ? 'success' : 'warning'}">{item.status}</span></td><td>{label(item.assignedField)}</td><td>{item.preferenceRank ? `#${item.preferenceRank}` : '—'}</td><td><button class="detail-button" onclick={() => (selected = item)}>View</button></td></tr>{/each}</tbody></table>
      {:else}<div class="empty"><div class="empty-icon">⌕</div><strong>No matching results</strong><p>Change or clear the current filters.</p></div>{/if}
    </div>
    <div class="pagination"><span>Page {Math.min(pageNumber, totalPages)} of {totalPages}</span><div><button class="button secondary" disabled={pageNumber <= 1} onclick={() => pageNumber--}>Previous</button><button class="button secondary" disabled={pageNumber >= totalPages} onclick={() => pageNumber++}>Next</button></div></div>
  </section>
</div>

{#if selected}
  <div class="drawer-backdrop" role="presentation" onclick={(event) => { if (event.target === event.currentTarget) selected = null; }}>
    <dialog class="drawer" open aria-labelledby="detail-title"><div class="drawer-head"><div><span class="badge {selected.status === 'assigned' ? 'success' : 'warning'}">{selected.status}</span><h2 id="detail-title">{selected.student.name}</h2><p>{selected.student.indexNumber} · {selected.student.email}</p></div><button aria-label="Close details" onclick={() => (selected = null)}>×</button></div><div class="drawer-body"><div class="outcome"><span>Allocation outcome</span><strong>{label(selected.assignedField)}</strong><small>{selected.preferenceRank ? `Student preference #${selected.preferenceRank}` : selected.reason}</small></div><h3>Academic evidence</h3><div class="grade-grid">{#each Object.entries(selected.grades) as [module, grade]}<div><span>{module}</span><strong>{grade}</strong></div>{/each}<div><span>SGPA</span><strong>{selected.sgpa.toFixed(2)}</strong></div></div><h3>Preference order</h3><ol>{#each selected.preferences as preference}<li class:chosen={preference === selected.assignedField}><span>{label(preference)}</span>{#if preference === selected.assignedField}<b>Assigned</b>{/if}</li>{/each}</ol><div class="authority-note"><strong>Response source</strong><p>This evidence is rendered from the API response. The frontend does not recalculate the decision.</p></div></div></dialog>
  </div>
{/if}

<style>
  .result-head { align-items: center; }
  .result-head > div:first-child { min-width: 150px; }
  .toolbar { justify-content: flex-end; }
  .toolbar .input { width: 205px; }
  .toolbar .select { min-width: 125px; max-width: 175px; font-size: .67rem; }
  .sgpa { color: var(--navy); font-family: 'Manrope'; font-weight: 800; }
  .detail-button { border: 0; background: transparent; color: var(--blue); cursor: pointer; font-size: .67rem; font-weight: 700; }
  .pagination { display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--line); padding: 14px 18px; }
  .pagination > span { color: #7c879a; font-size: .65rem; }
  .pagination > div { display: flex; gap: 7px; }
  .pagination .button { min-height: 34px; padding: 0 11px; font-size: .63rem; }
  .drawer-backdrop { position: fixed; z-index: 90; inset: 0; background: rgba(14,24,43,.43); }
  .drawer { position: absolute; top: 0; right: 0; left: auto; width: min(470px, 100%); height: 100%; max-height: none; margin: 0; overflow-y: auto; border: 0; background: #fff; padding: 0; color: inherit; box-shadow: -20px 0 60px rgba(10,20,38,.18); }
  .drawer-head { display: flex; align-items: flex-start; justify-content: space-between; border-bottom: 1px solid var(--line); padding: 28px; }
  .drawer-head h2 { margin: 13px 0 5px; font-size: 1.2rem; }
  .drawer-head p { margin: 0; color: #7f8a9d; font-size: .67rem; }
  .drawer-head button { border: 0; background: transparent; color: #788397; cursor: pointer; font-size: 1.5rem; }
  .drawer-body { padding: 24px 28px 40px; }
  .outcome { border-radius: 12px; background: var(--blue-soft); padding: 18px; }
  .outcome span, .outcome strong, .outcome small { display: block; }
  .outcome span { color: #7387aa; font-size: .59rem; text-transform: uppercase; }
  .outcome strong { margin: 6px 0 4px; font-size: .86rem; }
  .outcome small { color: #6e7f9d; font-size: .62rem; }
  .drawer-body h3 { margin: 24px 0 10px; font-size: .75rem; }
  .grade-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .grade-grid div { border: 1px solid var(--line); border-radius: 9px; padding: 10px; text-align: center; }
  .grade-grid span, .grade-grid strong { display: block; }
  .grade-grid span { color: #8a96a8; font-size: .53rem; }
  .grade-grid strong { margin-top: 4px; font-size: .75rem; }
  ol { margin: 0; padding: 0; list-style: none; counter-reset: pref; }
  ol li { display: flex; align-items: center; gap: 10px; border-bottom: 1px solid #edf0f4; padding: 10px 4px; color: #637087; font-size: .68rem; counter-increment: pref; }
  ol li::before { display: grid; width: 24px; height: 24px; place-items: center; border-radius: 50%; background: #f0f3f7; color: #778399; font-size: .55rem; content: counter(pref); }
  ol li.chosen { color: var(--green); font-weight: 700; }
  ol li b { margin-left: auto; border-radius: 99px; background: var(--green-soft); padding: 4px 7px; font-size: .53rem; }
  .authority-note { margin-top: 24px; border-radius: 10px; background: #f5f7fa; padding: 13px; }
  .authority-note strong { font-size: .64rem; }
  .authority-note p { margin: 4px 0 0; color: #7e899c; font-size: .61rem; line-height: 1.5; }
  @media (max-width: 1100px) { .result-head { align-items: flex-start; flex-direction: column; } .toolbar { justify-content: flex-start; width: 100%; } }
</style>
