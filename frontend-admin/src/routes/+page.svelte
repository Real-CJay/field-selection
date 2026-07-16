<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';
  import { session } from '$lib/stores';

  onMount(() => goto($session ? '/admin' : '/login', { replaceState: true }));
</script>

<div class="redirect" aria-live="polite">Opening FieldSelect…</div>

<style>
  .redirect { display: grid; min-height: 100vh; place-items: center; color: #67738b; }
</style>
