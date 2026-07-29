<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { getStudentEntryRoute } from '$lib/navigation';
  import { getModuleGrades, getStudentSession } from '$lib/session';

  onMount(() => {
    const session = getStudentSession();
    goto(getStudentEntryRoute(Boolean(session), Boolean(getModuleGrades())), {
      replaceState: true
    });
  });
</script>

<p class="loading">Loading…</p>

<style>
  .loading {
    padding: 40px;
    color: #6b7280;
    text-align: center;
  }
</style>
