<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { getStudentSession } from '$lib/session';

  onMount(() => {
    goto(getStudentSession() ? '/preferences' : '/login', { replaceState: true });
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
