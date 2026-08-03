<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { formatCutoff } from '$lib/allocation';
  import {
    getAdminDepartments,
    getAdminReport,
    getAdminStudents,
    updateAdminGrades,
    type AdminReportKind
  } from '$lib/admin-client';
  import { clearAdminSession, getAdminSession } from '$lib/admin-session';
  import { getCorrectionRequests, revertCorrectionRequest, reviewCorrectionRequest } from '$lib/correction-client';
  import { MODULE_GRADES } from '$lib/module-grades';
  import { DEPARTMENTS } from '$lib/preferences';
  import type {
    AdminDepartmentRecord,
    AdminDepartmentSummary,
    AdminStudentRecord,
    DepartmentId,
    GradeCorrectionRequest,
    ModuleGrade
  } from '$lib/types';

  type AdminSection = 'students' | 'requests' | 'departments';

  const subjectNames = {
    cse: 'CSE', maths: 'Mathematics', electrical: 'Electrical',
    fluids: 'Fluid Mechanics', mechanics: 'Mechanics', material: 'Material Science'
  } as const;
  const moduleNames = {
    cse: 'CSE', maths: 'Mathematics', electrical: 'Electrical', material: 'Material Science'
  } as const;
  const departmentNames = Object.fromEntries(DEPARTMENTS.map(({ id, name }) => [id, name])) as
    Record<DepartmentId, string>;

  let students = $state<AdminStudentRecord[]>([]);
  let requests = $state<GradeCorrectionRequest[]>([]);
  let departments = $state<AdminDepartmentRecord[]>([]);
  let departmentSummary = $state<AdminDepartmentSummary | null>(null);
  let studentSearch = $state('');
  let downloadingReport = $state<AdminReportKind | null>(null);
  let activeSection = $state<AdminSection>('students');
  let selectedDepartment = $state<DepartmentId | null>(null);
  let loading = $state(true);
  let message = $state('');
  let selectedRequests = $state<number[]>([]);
  let selectedDepartmentRecord = $derived(
    departments.find(({ department }) => department === selectedDepartment) ?? null
  );
  let filteredStudents = $derived.by(() => {
    const query = studentSearch.trim().toLowerCase();
    if (!query) return students;
    return students.filter((student) => {
      const searchable = [
        student.index_number,
        student.name,
        student.average_gpa === null ? '' : student.average_gpa.toFixed(4),
        student.average_gpa === null ? '' : student.average_gpa.toFixed(2),
        estimatedDepartment(student)
      ].join(' ').toLowerCase();
      return searchable.includes(query);
    });
  });

  onMount(async () => {
    if (!getAdminSession()) {
      await goto('/login', { replaceState: true });
      return;
    }
    await refresh();
  });

  async function refresh() {
    const adminSession = getAdminSession();
    if (!adminSession) return;
    loading = true;
    try {
      const [studentRecords, correctionRequests, departmentData] = await Promise.all([
        getAdminStudents(adminSession.token),
        getCorrectionRequests(adminSession.token),
        getAdminDepartments(adminSession.token)
      ]);
      students = studentRecords;
      requests = correctionRequests;
      departments = departmentData.departments;
      departmentSummary = departmentData.summary;
      if (selectedDepartment && !departments.some(({ department }) => department === selectedDepartment)) {
        selectedDepartment = null;
      }
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to load admin data.';
    } finally {
      loading = false;
    }
  }

  async function changeGrade(
    student: AdminStudentRecord,
    subject: keyof AdminStudentRecord['grades'],
    event: Event
  ) {
    const grade = (event.currentTarget as HTMLSelectElement).value as ModuleGrade;
    if (!confirm(`Change ${subjectNames[subject]} for ${student.index_number} to ${grade}?`)) {
      (event.currentTarget as HTMLSelectElement).value = student.grades[subject] === 'A / A+'
        ? 'A+'
        : student.grades[subject];
      return;
    }
    const adminSession = getAdminSession();
    if (!adminSession) return;
    loading = true;
    try {
      await updateAdminGrades(
        student.index_number, { [subject]: grade }, adminSession.token
      );
      await refresh();
      message = `${student.index_number} grade updated.`;
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to update the grade.';
      loading = false;
    }
  }

  async function review(id: number, decision: 'approved' | 'rejected') {
    const adminSession = getAdminSession();
    if (!adminSession) return;
    loading = true;
    try {
      await reviewCorrectionRequest(id, decision, adminSession.token);
      await refresh();
      message = `Request ${decision}.`;
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to review the request.';
      loading = false;
    }
  }

  async function bulkReview(decision: 'approved' | 'rejected') {
    const pendingIds = selectedRequests.filter((id) => requests.some((request) => request.id === id && request.status === 'pending'));
    if (!pendingIds.length || !confirm(`${decision === 'approved' ? 'Approve' : 'Reject'} ${pendingIds.length} selected requests?`)) return;
    const adminSession = getAdminSession();
    if (!adminSession) return;
    loading = true;
    try {
      await Promise.all(pendingIds.map((id) => reviewCorrectionRequest(id, decision, adminSession.token)));
      selectedRequests = [];
      await refresh();
      message = `${pendingIds.length} requests ${decision}.`;
    } catch (error) {
      await refresh();
      message = error instanceof Error ? error.message : 'Unable to complete the bulk review.';
    } finally {
      loading = false;
    }
  }

  async function revertCorrection(request: GradeCorrectionRequest) {
    if (!confirm(`Revert ${moduleNames[request.module]} for ${request.index_number} from ${request.requested_grade} back to ${request.current_grade}?`)) return;
    const adminSession = getAdminSession();
    if (!adminSession) return;
    loading = true;
    try {
      await revertCorrectionRequest(request.id, adminSession.token);
      await refresh();
      message = 'The approved correction was reverted. Its history has been preserved.';
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to revert the correction.';
      loading = false;
    }
  }

  function estimatedDepartment(student: AdminStudentRecord): string {
    const allocation = student.allocation;
    if (student.average_gpa === null || student.preferences.length === 0) return 'Incomplete';
    if (allocation.assigned_department) return `Assigned: ${departmentNames[allocation.assigned_department]}`;
    if (allocation.possible_departments.length) return `Possible: ${allocation.possible_departments.map((id) => departmentNames[id]).join(', ')}`;
    if (allocation.guaranteed_department) return `Current estimate: ${departmentNames[allocation.guaranteed_department]} or higher`;
    return 'Unresolved';
  }

  function logout() {
    clearAdminSession();
    goto('/login');
  }

  function openDepartment(department: DepartmentId) {
    selectedDepartment = department;
  }

  async function downloadReport(kind: AdminReportKind) {
    const adminSession = getAdminSession();
    if (!adminSession) return;
    downloadingReport = kind;
    try {
      const report = await getAdminReport(kind, adminSession.token);
      const url = URL.createObjectURL(report.blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = report.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      message = kind === 'student-rankings'
        ? 'Detailed ranked-student report downloaded.'
        : 'Department summary report downloaded.';
    } catch (error) {
      message = error instanceof Error ? error.message : 'Unable to download the report.';
    } finally {
      downloadingReport = null;
    }
  }

  function selectionCount(department: AdminDepartmentRecord): string {
    return department.selected_min === department.selected_max
      ? `${department.selected_max} selected`
      : `${department.selected_min}–${department.selected_max} possible`;
  }
</script>

<svelte:head><title>Admin · Field Selection</title></svelte:head>

<main class="page admin-page">
  <header class="admin-header">
    <div>
      <p class="eyebrow">Administration</p>
      <h1>Field Selection Admin</h1>
      <p class="muted">Review records, recorrection requests, and live department allocations.</p>
    </div>
    <button class="button secondary" type="button" onclick={logout}>Log out</button>
  </header>

  <nav class="section-nav" aria-label="Admin sections">
    <button class:active={activeSection === 'students'} type="button" onclick={() => activeSection = 'students'}>
      <span>Student full records</span><small>{students.length}</small>
    </button>
    <button class:active={activeSection === 'requests'} type="button" onclick={() => activeSection = 'requests'}>
      <span>Recorrection requests</span><small>{requests.filter(({ status }) => status === 'pending').length} pending</small>
    </button>
    <button class:active={activeSection === 'departments'} type="button" onclick={() => activeSection = 'departments'}>
      <span>Departments</span><small>{departments.length}</small>
    </button>
  </nav>

  {#if message}<p class="message" role="status">{message}</p>{/if}
  {#if loading && students.length === 0}<p class="status">Loading admin data…</p>{/if}

  {#if activeSection === 'students'}
    <section class="card admin-section" aria-labelledby="students-heading">
      <div class="section-heading">
        <div><h2 id="students-heading">Student full records</h2><p class="muted">Complete grades, ranked preferences, submission time, and current allocation.</p></div>
        <div class="section-actions">
          <label class="student-search">
            <span>Search students</span>
            <input
              class="input"
              type="search"
              placeholder="Index, name, GPA, or department"
              bind:value={studentSearch}
            />
          </label>
          <button class="button secondary" type="button" disabled={loading} onclick={refresh}>Refresh</button>
        </div>
      </div>
      <p class="record-count">Showing {filteredStudents.length} of {students.length} students</p>
      <div class="table-wrap">
        <table class="student-table">
          <thead><tr><th>Student</th><th>GPA</th><th>Grades</th><th>Preferences</th><th>Submitted</th><th>Estimated department</th></tr></thead>
          <tbody>
            {#each filteredStudents as student}
              <tr>
                <td><strong>{student.index_number}</strong><small>{student.name}</small></td>
                <td>{student.average_gpa === null ? 'Incomplete' : student.average_gpa.toFixed(4)}</td>
                <td>
                  <div class="grade-grid">
                    {#each Object.entries(subjectNames) as [subject, label]}
                      <label>{label}
                        <select class="select grade-select"
                          value={student.grades[subject as keyof typeof subjectNames] === 'A / A+' ? 'A+' : student.grades[subject as keyof typeof subjectNames]}
                          disabled={loading}
                          onchange={(event) => changeGrade(student, subject as keyof AdminStudentRecord['grades'], event)}>
                          {#each MODULE_GRADES as grade}<option value={grade}>{grade}</option>{/each}
                        </select>
                      </label>
                    {/each}
                  </div>
                </td>
                <td>
                  {#if student.preferences.length}
                    <ol>{#each student.preferences as preference}<li>{departmentNames[preference]}</li>{/each}</ol>
                  {:else}<span class="muted">Incomplete</span>{/if}
                </td>
                <td>{student.submitted_at ? new Date(student.submitted_at).toLocaleString() : 'Incomplete'}</td>
                <td>
                  <strong>{estimatedDepartment(student)}</strong>
                  <small class="status-label">Allocation state: {student.allocation.allocation_status}</small>
                </td>
              </tr>
            {/each}
            {#if filteredStudents.length === 0}
              <tr><td class="empty-row" colspan="6">No students match your search.</td></tr>
            {/if}
          </tbody>
        </table>
      </div>
    </section>
  {:else if activeSection === 'requests'}
    <section class="card admin-section" aria-labelledby="requests-heading">
      <div class="section-heading">
        <div><h2 id="requests-heading">Recorrection requests</h2><p class="muted">Every request remains in this history. Select pending requests for bulk review, or revert an approved grade when it has not changed again.</p></div>
        <div class="review-actions">
          <button class="button" disabled={loading || selectedRequests.length === 0} onclick={() => bulkReview('approved')}>Approve selected</button>
          <button class="button secondary" disabled={loading || selectedRequests.length === 0} onclick={() => bulkReview('rejected')}>Reject selected</button>
        </div>
      </div>
      {#if requests.length === 0}<p>No recorrection requests yet.</p>{/if}
      <div class="request-list">
        {#each requests as request}
          <article class="request">
            {#if request.status === 'pending'}
              <input class="request-check" type="checkbox" aria-label={`Select request ${request.id}`} checked={selectedRequests.includes(request.id)} onchange={(event) => selectedRequests = (event.currentTarget as HTMLInputElement).checked ? [...selectedRequests, request.id] : selectedRequests.filter((id) => id !== request.id)} />
            {:else}<span class="request-check-spacer" aria-hidden="true"></span>{/if}
            <div>
              <strong>{request.index_number} · {moduleNames[request.module]}</strong>
              <p>{request.current_grade} → {request.requested_grade}</p>
              <small>
                Requested {new Date(request.created_at).toLocaleString()} · {request.status}
                {#if request.reviewed_at} · reviewed {new Date(request.reviewed_at).toLocaleString()}{/if}
                {#if request.reverted_at} · reverted {new Date(request.reverted_at).toLocaleString()}{/if}
              </small>
            </div>
            {#if request.status === 'pending'}
              <div class="review-actions">
                <button class="button" disabled={loading} onclick={() => review(request.id, 'approved')}>Approve</button>
                <button class="button secondary" disabled={loading} onclick={() => review(request.id, 'rejected')}>Reject</button>
              </div>
            {:else if request.status === 'approved'}
              <button class="button secondary" disabled={loading} onclick={() => revertCorrection(request)}>Revert grade</button>
            {/if}
          </article>
        {/each}
      </div>
    </section>
  {:else}
    <section class="card admin-section" aria-labelledby="departments-heading">
      <div class="section-heading">
        <div><h2 id="departments-heading">Departments and selected students</h2><p class="muted">Choose a department to inspect its current allocation and boundary outcomes.</p></div>
        <div class="report-actions">
          <button
            class="button secondary"
            type="button"
            disabled={loading || downloadingReport !== null}
            onclick={() => downloadReport('student-rankings')}
          >{downloadingReport === 'student-rankings' ? 'Preparing…' : 'Download detailed rankings CSV'}</button>
          <button
            class="button secondary"
            type="button"
            disabled={loading || downloadingReport !== null}
            onclick={() => downloadReport('department-summary')}
          >{downloadingReport === 'department-summary' ? 'Preparing…' : 'Download department summary CSV'}</button>
        </div>
      </div>
      {#if departmentSummary}
        <div class="summary-grid" aria-label="Department allocation summary">
          <div class="summary-card">
            <span>Eligible cohort processed</span>
            <strong>{departmentSummary.total_students_processed} / {departmentSummary.total_cohort}</strong>
          </div>
          <div class="summary-card">
            <span>Cohort coverage</span>
            <strong>{departmentSummary.coverage_percentage.toFixed(1)}% · {departmentSummary.coverage_band}</strong>
            <small>{departmentSummary.coverage_note}</small>
          </div>
          <div class="summary-card">
            <span>Currently allocated</span>
            <strong>
              {departmentSummary.selected_min === departmentSummary.selected_max
                ? departmentSummary.selected_max
                : `${departmentSummary.selected_min}–${departmentSummary.selected_max}`}
            </strong>
          </div>
          <div class="summary-card">
            <span>Total department capacity</span>
            <strong>{departmentSummary.total_capacity}</strong>
          </div>
        </div>
      {/if}
      <div class="department-grid">
        {#each departments as department}
          <button class:selected={selectedDepartment === department.department} type="button" onclick={() => openDepartment(department.department)}>
            <strong>{departmentNames[department.department]}</strong>
            <span>{selectionCount(department)} of {department.quota} seats</span>
            <small>Cut-off: {formatCutoff(department.cutoff)}</small>
          </button>
        {/each}
      </div>

      {#if selectedDepartmentRecord}
        <section class="department-detail" aria-labelledby="department-detail-heading">
          <div class="department-detail-heading">
            <div>
              <p class="eyebrow">Current selection</p>
              <h3 id="department-detail-heading">{departmentNames[selectedDepartmentRecord.department]}</h3>
            </div>
            <div class="seat-summary"><strong>{selectionCount(selectedDepartmentRecord)}</strong><span>Quota {selectedDepartmentRecord.quota}</span></div>
          </div>
          {#if selectedDepartmentRecord.incomplete}
            <p class="boundary-warning">Some linked tie outcomes reached the allocation safety limit, so this list may be incomplete.</p>
          {/if}
          {#if selectedDepartmentRecord.students.length === 0}
            <p>No students are currently selected for this department.</p>
          {:else}
            <div class="table-wrap">
              <table class="department-table">
                <thead><tr><th>Department rank</th><th>Student</th><th>Average GPA</th><th>Allocation GPA</th><th>Selection</th><th>Tie-break</th></tr></thead>
                <tbody>
                  {#each selectedDepartmentRecord.students as student, index}
                    <tr class:border-row={student.selection_status === 'border'}>
                      <td><strong>{index + 1}</strong></td>
                      <td><strong>{student.index_number}</strong><small>{student.name}</small></td>
                      <td>{student.average_gpa.toFixed(4)}</td>
                      <td>{student.allocation_gpa.toFixed(2)}</td>
                      <td>
                        <span class:boundary-badge={student.selection_status === 'border'} class="selection-badge">
                          {student.selection_status === 'selected' ? 'Selected' : 'Border outcome'}
                        </span>
                        {#if student.selection_status === 'border'}
                          <small>Selected in {student.selected_state_count} of {student.total_states} valid outcomes</small>
                        {/if}
                      </td>
                      <td>
                        {#if student.tiebreaker}
                          <span class="tie-indicator">
                            <button class="tie-trigger" type="button" aria-label={`View tie-break result for ${student.index_number}`}>Tie-break ⓘ</button>
                            <span class="tie-tooltip" role="tooltip">
                              <strong>Department tie-break score: {student.tiebreaker.score.toFixed(4)}</strong>
                              {#each student.tiebreaker.subjects as subject}
                                <span>{subjectNames[subject.subject]}: {subject.grade} ({subject.value.toFixed(1)})</span>
                              {/each}
                              <span>{student.tiebreaker.candidate_count} students share this cutoff GPA.</span>
                              {#if student.tiebreaker.score_tied}<em>The subject score is also tied, so multiple valid outcomes remain.</em>{/if}
                            </span>
                          </span>
                        {:else}<span class="muted">Not required</span>{/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        </section>
      {:else}
        <p class="department-prompt">Select a department above to see its students.</p>
      {/if}
    </section>
  {/if}
</main>

<style>
  .admin-page { max-width: 1500px; }
  .admin-header, .section-heading, .department-detail-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
  .admin-header { margin-bottom: 20px; }
  .admin-header h1, .admin-header p, .section-heading h2, .section-heading p { margin-bottom: 0; }
  .eyebrow { margin: 0 0 5px; color: #1d4ed8; font-size: .75rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
  .section-nav { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 20px 0; }
  .section-nav button { display: flex; align-items: center; justify-content: space-between; gap: 12px; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; padding: 14px 16px; color: #374151; cursor: pointer; font: inherit; font-weight: 700; text-align: left; }
  .section-nav button:hover { border-color: #93c5fd; background: #f8fbff; }
  .section-nav button.active { border-color: #2563eb; background: #eff6ff; color: #1e3a8a; }
  .section-nav small { color: #6b7280; font-size: .75rem; font-weight: 600; }
  .admin-section { margin-top: 20px; }
  .section-actions { display: flex; align-items: flex-end; gap: 10px; }
  .student-search { display: grid; min-width: 310px; gap: 5px; color: #374151; font-size: .78rem; font-weight: 700; }
  .student-search .input { min-width: 0; margin: 0; }
  .record-count { margin: 14px 0 0; color: #6b7280; font-size: .85rem; }
  .empty-row { padding: 28px; color: #6b7280; text-align: center; }
  .report-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
  .summary-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-top: 20px; }
  .summary-card { display: grid; align-content: start; gap: 5px; border: 1px solid #dbeafe; border-radius: 8px; background: #f8fbff; padding: 14px; }
  .summary-card span { color: #4b5563; font-size: .78rem; font-weight: 700; }
  .summary-card strong { color: #1e3a8a; font-size: 1.2rem; }
  .summary-card small { color: #6b7280; font-size: .72rem; line-height: 1.35; }
  .table-wrap { margin-top: 18px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; }
  .student-table { min-width: 1260px; }
  .department-table { min-width: 860px; }
  th, td { border-bottom: 1px solid #e5e7eb; padding: 12px; text-align: left; vertical-align: top; }
  th { background: #f9fafb; color: #4b5563; font-size: .82rem; }
  td small { display: block; margin-top: 4px; color: #6b7280; }
  td ol { min-width: 260px; margin: 0; padding-left: 22px; }
  .grade-grid { display: grid; min-width: 360px; grid-template-columns: repeat(2, 1fr); gap: 8px; }
  .grade-grid label { font-size: .72rem; font-weight: 600; }
  .grade-select { margin-top: 3px; padding: 7px; }
  .status-label { text-transform: capitalize; }
  .request-list { display: grid; gap: 12px; margin-top: 18px; }
  .request { display: flex; align-items: center; justify-content: space-between; gap: 20px; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; }
  .request > div:first-of-type { flex: 1; }
  .request-check, .request-check-spacer { flex: 0 0 18px; width: 18px; height: 18px; }
  .request p { margin: 5px 0; }
  .request small { color: #6b7280; }
  .review-actions { display: flex; gap: 8px; }
  .status, .department-prompt { color: #6b7280; }
  .department-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; margin-top: 20px; }
  .department-grid button { display: grid; gap: 6px; border: 1px solid #d1d5db; border-radius: 8px; background: #fff; padding: 16px; color: #111827; cursor: pointer; font: inherit; text-align: left; }
  .department-grid button:hover, .department-grid button.selected { border-color: #2563eb; box-shadow: 0 0 0 2px #dbeafe; }
  .department-grid button.selected { background: #eff6ff; }
  .department-grid span, .department-grid small { color: #6b7280; }
  .department-detail { margin-top: 24px; border-top: 1px solid #e5e7eb; padding-top: 22px; }
  .department-detail h3 { margin: 0; font-size: 1.35rem; }
  .seat-summary { min-width: 140px; border: 1px solid #bfdbfe; border-radius: 8px; background: #eff6ff; padding: 10px 14px; text-align: right; }
  .seat-summary strong, .seat-summary span { display: block; }
  .seat-summary span { margin-top: 2px; color: #6b7280; font-size: .8rem; }
  .boundary-warning { border: 1px solid #f59e0b; border-radius: 7px; background: #fffbeb; padding: 12px 14px; color: #78350f; }
  .selection-badge { display: inline-block; border-radius: 999px; background: #dcfce7; padding: 4px 9px; color: #166534; font-size: .78rem; font-weight: 700; }
  .selection-badge.boundary-badge { background: #fef3c7; color: #92400e; }
  tr.border-row td { background: #fffdf5; }
  .tie-indicator { position: relative; display: inline-block; }
  .tie-trigger { border: 1px solid #f59e0b; border-radius: 999px; background: #fffbeb; padding: 5px 9px; color: #92400e; cursor: help; font: inherit; font-size: .78rem; font-weight: 700; }
  .tie-trigger:focus-visible { outline: 3px solid #93c5fd; outline-offset: 2px; }
  .tie-tooltip { position: absolute; z-index: 10; right: 0; bottom: calc(100% + 8px); display: grid; width: 300px; gap: 5px; border-radius: 8px; background: #111827; padding: 12px; color: #fff; font-size: .78rem; line-height: 1.4; opacity: 0; pointer-events: none; transform: translateY(4px); transition: opacity .15s, transform .15s; }
  .tie-tooltip::after { position: absolute; right: 22px; bottom: -6px; width: 12px; height: 12px; background: #111827; content: ''; transform: rotate(45deg); }
  .tie-tooltip em { color: #fde68a; }
  .tie-indicator:hover .tie-tooltip, .tie-indicator:focus-within .tie-tooltip { opacity: 1; transform: translateY(0); }
  @media (max-width: 760px) {
    .admin-header, .section-heading, .department-detail-heading, .request { align-items: stretch; flex-direction: column; }
    .section-actions, .report-actions { align-items: stretch; flex-direction: column; }
    .student-search { min-width: 0; }
    .summary-grid { grid-template-columns: 1fr 1fr; }
    .section-nav { grid-template-columns: 1fr; }
    .review-actions .button { flex: 1; }
    .tie-tooltip { right: auto; left: 0; width: min(280px, 75vw); }
  }
  @media (max-width: 480px) {
    .summary-grid { grid-template-columns: 1fr; }
  }
</style>
