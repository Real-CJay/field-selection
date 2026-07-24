<script lang="ts">
  import type { AllocationErrorState } from '$lib/allocation';

  let {
    state,
    onBack,
    onRetry
  }: {
    state: AllocationErrorState;
    onBack?: () => void;
    onRetry?: () => void;
  } = $props();
</script>

<section class="status-card" class:not-found={state === 'not-found'} role="alert">
  {#if state === 'not-found'}
    <h2>No allocation result found</h2>
    <p>
      We could not find submitted allocation data for this student. Check that preferences were
      submitted before trying again.
    </p>
    {#if onBack}
      <button class="button secondary" type="button" onclick={onBack}>Back to preferences</button>
    {/if}
  {:else}
    <h2>Unable to load allocation results</h2>
    <p>Something went wrong while loading the result. Please try again.</p>
    {#if onRetry}
      <button class="button" type="button" onclick={onRetry}>Retry</button>
    {/if}
  {/if}
</section>

<style>
  .status-card {
    border: 1px solid #fca5a5;
    border-radius: 8px;
    background: #fef2f2;
    padding: 24px;
    color: #991b1b;
  }

  .status-card.not-found {
    border-color: #facc15;
    background: #fefce8;
    color: #713f12;
  }

  h2 {
    margin-bottom: 8px;
    font-size: 1.2rem;
  }

  p {
    margin-bottom: 18px;
    line-height: 1.5;
  }
</style>
