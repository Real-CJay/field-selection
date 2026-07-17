<script lang="ts">
  import '../app.css';
  let { children } = $props();
</script>

<svelte:head>
  <title>FieldSelect Admin</title>
  <meta name="description" content="Mock-first field selection administration console" />
</svelte:head>

{@render children()}
