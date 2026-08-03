<script lang="ts">
  import '../app.css';
  let { children } = $props();
</script>

<svelte:head>
  <title>Field Selection</title>
  <meta name="description" content="Student field preference selection" />
</svelte:head>

{@render children()}
