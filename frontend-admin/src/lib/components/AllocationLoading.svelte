<script lang="ts">
  import {
    ALLOCATION_LOADING_DESCRIPTION,
    ALLOCATION_LOADING_TITLE
  } from '$lib/allocation';
</script>

<section class="loading-card" aria-live="polite" aria-busy="true">
  <span class="spinner" aria-hidden="true"></span>
  <div>
    <h2>{ALLOCATION_LOADING_TITLE}</h2>
    <p>{ALLOCATION_LOADING_DESCRIPTION}</p>
  </div>
</section>

<style>
  .loading-card {
    display: flex;
    align-items: center;
    gap: 18px;
    border: 1px solid #bfdbfe;
    border-radius: 8px;
    background: #eff6ff;
    padding: 24px;
    color: #1e3a8a;
  }

  .spinner {
    width: 34px;
    height: 34px;
    flex: 0 0 auto;
    border: 4px solid #bfdbfe;
    border-top-color: #1d4ed8;
    border-radius: 50%;
    animation: spin 0.9s linear infinite;
  }

  h2 {
    margin: 0 0 6px;
    font-size: 1.1rem;
  }

  p {
    margin: 0;
    color: #374151;
    line-height: 1.5;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  @media (prefers-reduced-motion: reduce) {
    .spinner {
      animation: none;
    }
  }

  @media (max-width: 520px) {
    .loading-card {
      align-items: flex-start;
      padding: 20px;
    }
  }
</style>
