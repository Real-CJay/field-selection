<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { getReturningStudentRoute } from '$lib/navigation';
  import { getModuleGrades, getStudentSession } from '$lib/session';
  import { studentRepository } from '$lib/student-repository';

  onMount(async () => {
    const session = getStudentSession();
    if (!session) {
      await goto('/login', { replaceState: true });
      return;
    }

    try {
      const route = await getReturningStudentRoute(
        session.indexNumber,
        studentRepository.getResults,
        studentRepository.getPreferences
      );
      await goto(route, { replaceState: true });
    } catch {
      await goto(getModuleGrades() ? '/preferences' : '/module-grades', { replaceState: true });
    }
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
