<script lang="ts">
  import { api } from '$lib/api/client';
  import type { ImportReport, ImportType } from '$lib/types';

  const configs: Record<ImportType, { label: string; description: string; fields: string[] }> = {
    students: { label: 'Student accounts', description: 'Index numbers, names, and institutional email addresses', fields: ['Index Number', 'Name', 'Email'] },
    results: { label: 'Academic results', description: 'Index numbers, module grades, and calculated SGPA', fields: ['Index Number', 'MA', 'CS', 'EE'] },
    preferences: { label: 'Field preferences', description: 'Index numbers and ranked field choices', fields: ['Index Number', 'First Choice', 'Second Choice'] }
  };

  let type = $state<ImportType>('students');
  let file = $state<File | null>(null);
  let dragging = $state(false);
  let loading = $state(false);
  let uploading = $state(false);
  let error = $state('');
  let report = $state<ImportReport | null>(null);
  let success = $state('');
  let mapping = $state<Record<string, string>>({});

  function setType(value: ImportType) { type = value; file = null; report = null; error = ''; mapping = {}; }
  function choose(files: FileList | null) { const chosen = files?.[0]; if (!chosen) return; file = chosen; report = null; error = ''; success = ''; }
  function drop(event: DragEvent) { event.preventDefault(); dragging = false; choose(event.dataTransfer?.files ?? null); }

  async function validate() {
    if (!file) return;
    loading = true; error = ''; report = null;
    const fields = configs[type].fields;
    mapping = Object.fromEntries(fields.map((field, index) => [field, String(index)]));
    try { report = await api.validateImport(type, file, mapping); }
    catch (value) { error = value instanceof Error ? value.message : 'The file could not be validated.'; }
    finally { loading = false; }
  }

  async function upload() {
    if (!report) return;
    uploading = true; error = '';
    try { await api.uploadImport(report); success = `${report.validRows} ${configs[type].label.toLowerCase()} were accepted by the mock API.`; report = null; file = null; }
    catch (value) { error = value instanceof Error ? value.message : 'The import could not be completed.'; }
    finally { uploading = false; }
  }
</script>

<svelte:head><title>Data imports · FieldSelect Admin</title></svelte:head>

<div class="page">
  <div class="page-header"><div><div class="eyebrow">Data preparation</div><h1>Import and validate data</h1><p>Inspect CSV structure before anything is sent to the backend.</p></div><span class="badge info">Maximum file size 5 MB</span></div>

  <div class="import-grid">
    <aside class="panel type-panel">
      <div class="panel-head"><div><h2>Import type</h2><p>Choose the dataset to test</p></div></div>
      <div class="type-list">
        {#each Object.entries(configs) as [key, config]}
          <button class:active={type === key} onclick={() => setType(key as ImportType)}><span>{key === 'students' ? '♙' : key === 'results' ? '▤' : '☷'}</span><div><strong>{config.label}</strong><small>{config.description}</small></div><i>›</i></button>
        {/each}
      </div>
      <div class="privacy-note"><strong>Privacy reminder</strong><p>Use fictional test records only. Uploaded files remain in browser memory in mock mode.</p></div>
    </aside>

    <section class="panel upload-panel">
      <div class="panel-head"><div><h2>{configs[type].label}</h2><p>{configs[type].description}</p></div>{#if report}<span class="badge {report.invalidRows ? 'warning' : 'success'}">Validation complete</span>{/if}</div>
      <div class="panel-body">
        <div class:dragging class="dropzone" role="region" aria-label="CSV upload drop zone" ondragover={(event) => { event.preventDefault(); dragging = true; }} ondragleave={() => (dragging = false)} ondrop={drop}>
          <input id="csv-file" type="file" accept=".csv,text/csv" onchange={(event) => choose(event.currentTarget.files)} />
          <div class="upload-icon">⇧</div>
          {#if file}<strong>{file.name}</strong><p>{(file.size / 1024).toFixed(1)} KB · Ready to validate</p><label for="csv-file">Choose another file</label>{:else}<strong>Drop a CSV file here</strong><p>or select one from your computer</p><label for="csv-file">Browse files</label>{/if}
        </div>

        <div class="requirements"><strong>Expected columns</strong><div>{#each configs[type].fields as field}<code>{field}</code>{/each}</div></div>
        {#if error}<div class="form-error" role="alert"><strong>!</strong> {error}</div>{/if}
        <div class="upload-action"><p>Files are validated locally by the simulated API and are not saved.</p><button class="button primary" disabled={!file || loading} onclick={validate}>{loading ? 'Validating file…' : 'Validate and preview'}</button></div>

        {#if report}
          <section class="report" aria-live="polite">
            <div class="report-metrics"><div><span>Total rows</span><strong>{report.totalRows}</strong></div><div><span>Valid</span><strong class="green">{report.validRows}</strong></div><div><span>Invalid</span><strong class="red">{report.invalidRows}</strong></div><div><span>Duplicates</span><strong class="amber">{report.duplicateRows}</strong></div></div>
            <h3>Column mapping</h3>
            <div class="mapping">{#each configs[type].fields as field}<label><span>{field}</span><select class="select" bind:value={mapping[field]}>{#each configs[type].fields as option, index}<option value={index}>{option}</option>{/each}</select></label>{/each}</div>
            <h3>Data preview</h3>
            <div class="table-wrap"><table><thead><tr>{#each Object.keys(report.preview[0] ?? {}) as header}<th>{header}</th>{/each}</tr></thead><tbody>{#each report.preview as row}<tr>{#each Object.values(row) as value}<td>{value || '—'}</td>{/each}</tr>{/each}</tbody></table></div>
            {#if report.issues.length}<div class="issues"><strong>Validation issues</strong>{#each report.issues.slice(0, 4) as issue}<p>Row {issue.row} · {issue.message}</p>{/each}</div>{/if}
            <div class="report-action"><span>{report.invalidRows || report.duplicateRows ? 'Only valid rows will be accepted.' : 'All rows are ready.'}</span><button class="button primary" disabled={uploading || report.validRows === 0} onclick={upload}>{uploading ? 'Uploading…' : `Import ${report.validRows} rows`}</button></div>
          </section>
        {/if}
      </div>
    </section>
  </div>
</div>

{#if success}<div class="toast" role="status"><span>✓</span>{success}<button aria-label="Dismiss notification" onclick={() => (success = '')}>×</button></div>{/if}

<style>
  .import-grid { display: grid; grid-template-columns: 310px minmax(0, 1fr); gap: 16px; align-items: start; }
  .type-list { display: grid; gap: 4px; padding: 12px; }
  .type-list button { display: grid; grid-template-columns: 35px 1fr auto; align-items: center; gap: 11px; width: 100%; border: 1px solid transparent; border-radius: 10px; background: transparent; padding: 11px; color: #526079; cursor: pointer; text-align: left; }
  .type-list button:hover, .type-list button.active { border-color: #dbe5f8; background: var(--blue-soft); color: var(--blue); }
  .type-list button > span { display: grid; height: 34px; place-items: center; border-radius: 9px; background: #f0f3f7; }
  .type-list button.active > span { background: #dfe9ff; }
  .type-list strong, .type-list small { display: block; }
  .type-list strong { margin-bottom: 3px; font-size: .71rem; }
  .type-list small { color: #8c97a9; font-size: .58rem; line-height: 1.4; }
  .type-list i { font-style: normal; }
  .privacy-note { margin: 3px 12px 14px; border-radius: 10px; background: #fff7e9; padding: 13px; }
  .privacy-note strong { color: #9f651d; font-size: .67rem; }
  .privacy-note p { margin: 5px 0 0; color: #9b7b51; font-size: .6rem; line-height: 1.5; }
  .dropzone { position: relative; display: grid; min-height: 220px; place-items: center; align-content: center; border: 2px dashed #d4dce8; border-radius: 13px; background: #fafbfd; padding: 28px; text-align: center; transition: 150ms; }
  .dropzone.dragging { border-color: var(--blue); background: var(--blue-soft); }
  .dropzone input { position: absolute; width: 1px; height: 1px; opacity: 0; }
  .upload-icon { display: grid; width: 45px; height: 45px; margin-bottom: 12px; place-items: center; border-radius: 13px; background: var(--blue-soft); color: var(--blue); font-size: 1.2rem; }
  .dropzone strong { font-size: .82rem; }
  .dropzone p { margin: 5px 0 13px; color: #8994a7; font-size: .68rem; }
  .dropzone label { border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 7px 12px; color: #4f5d74; cursor: pointer; font-size: .67rem; font-weight: 700; }
  .requirements { display: flex; align-items: center; gap: 14px; margin-top: 18px; }
  .requirements > strong { color: #69758b; font-size: .67rem; }
  .requirements div { display: flex; gap: 6px; flex-wrap: wrap; }
  .requirements code { border-radius: 6px; background: #f1f3f7; padding: 5px 7px; color: #5c6980; font-size: .59rem; }
  .upload-action, .report-action { display: flex; align-items: center; justify-content: space-between; gap: 18px; margin-top: 20px; border-top: 1px solid #edf0f4; padding-top: 18px; }
  .upload-action p, .report-action span { margin: 0; color: #8a95a8; font-size: .64rem; }
  .report { margin-top: 24px; border-top: 1px solid var(--line); padding-top: 24px; }
  .report-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 9px; }
  .report-metrics div { border-radius: 10px; background: #f7f8fa; padding: 12px; }
  .report-metrics span, .report-metrics strong { display: block; }
  .report-metrics span { color: #8590a4; font-size: .58rem; }
  .report-metrics strong { margin-top: 5px; font-size: 1rem; }
  .green { color: var(--green); } .red { color: var(--red); } .amber { color: var(--amber); }
  .report h3 { margin: 21px 0 10px; font-size: .78rem; }
  .mapping { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .mapping label span { display: block; margin-bottom: 5px; color: #718097; font-size: .6rem; }
  .mapping .select { min-height: 36px; font-size: .67rem; }
  .issues { margin-top: 14px; border-radius: 10px; background: var(--amber-soft); padding: 13px; color: #946225; }
  .issues strong { font-size: .67rem; }
  .issues p { margin: 5px 0 0; font-size: .61rem; }
  .toast button { margin-left: auto; border: 0; background: transparent; color: inherit; cursor: pointer; font-size: 1rem; }
  @media (max-width: 980px) { .import-grid { grid-template-columns: 1fr; } .type-list { grid-template-columns: repeat(3, 1fr); } .type-list button { grid-template-columns: 30px 1fr; } .type-list button i { display: none; } .privacy-note { display: none; } }
  @media (max-width: 650px) { .type-list { grid-template-columns: 1fr; } .report-metrics { grid-template-columns: repeat(2, 1fr); } .mapping { grid-template-columns: 1fr; } .upload-action, .report-action { align-items: stretch; flex-direction: column; } }
</style>
