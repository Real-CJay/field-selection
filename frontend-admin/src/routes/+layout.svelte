<script lang="ts">
  import { env } from '$env/dynamic/public';
  import { page } from '$app/state';
  import { isMaintenancePreviewStudent } from '$lib/maintenance-access';
  import { getStudentSession } from '$lib/session';
  import '../app.css';
  let { children } = $props();
  // Stay closed by default in production. Local testing enables the app with
  // PUBLIC_MAINTENANCE_MODE=false in the ignored .env file.
  const maintenanceMode = env.PUBLIC_MAINTENANCE_MODE !== 'false';
  // The root route forwards to /login, so it must also render while maintenance is enabled.
  let showEntryRoute = $derived(
    page.url.pathname === '/'
      || page.url.pathname === '/login'
      || page.url.pathname === '/auth/callback'
      || page.url.pathname === '/admin'
  );
  let hasPreviewAccess = $derived.by(() => {
    // Make this re-evaluate after route navigation, when login updates local storage.
    page.url.pathname;
    return isMaintenancePreviewStudent(getStudentSession()?.indexNumber);
  });
  let showMaintenance = $derived(maintenanceMode && !showEntryRoute && !hasPreviewAccess);
</script>

<svelte:head>
  <title>Field Selection</title>
  <meta name="description" content="Student field preference selection" />
</svelte:head>

{#if showMaintenance}
  <main class="maintenance" aria-labelledby="maintenance-heading">
    <section class="maintenance-card">
      <p class="eyebrow">Field Selection</p>
      <h1 id="maintenance-heading">Site is currently under maintenance</h1>
      <p>
        We are fixing a few issues to keep the allocation information accurate. Please check
        back shortly.
      </p>
    </section>
  </main>
{:else}
  {@render children()}
{/if}

<style>
  .maintenance {
    display: grid;
    min-height: 100vh;
    place-items: center;
    padding: 24px;
  }

  .maintenance-card {
    width: min(100%, 560px);
    border: 1px solid #d1d5db;
    border-radius: 12px;
    background: #fff;
    padding: 32px;
    text-align: center;
  }

  .maintenance-card h1 { margin: 8px 0 14px; }
  .maintenance-card p:last-child { color: #4b5563; }
</style>
