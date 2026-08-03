<script lang="ts">
  import { env } from '$env/dynamic/public';
  import { onMount } from 'svelte';

  type TurnstileApi = {
    render: (element: HTMLElement, options: Record<string, unknown>) => string;
    remove: (widgetId: string) => void;
  };

  type TurnstileWindow = Window & typeof globalThis & { turnstile?: TurnstileApi };

  function turnstileWindow(): TurnstileWindow {
    return window as TurnstileWindow;
  }

  let {
    onToken,
    action = 'student-auth'
  }: {
    onToken: (token: string) => void;
    action?: string;
  } = $props();

  let container: HTMLDivElement;
  let message = $state('Loading security check…');
  let scriptLoader: Promise<void> | null = null;

  function loadScript(): Promise<void> {
    if (turnstileWindow().turnstile) return Promise.resolve();
    if (scriptLoader) return scriptLoader;
    scriptLoader = new Promise((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>('script[data-field-selection-turnstile]');
      if (existing) {
        existing.addEventListener('load', () => resolve(), { once: true });
        existing.addEventListener('error', () => reject(new Error('Turnstile failed to load.')), { once: true });
        return;
      }
      const script = document.createElement('script');
      script.src = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';
      script.async = true;
      script.defer = true;
      script.dataset.fieldSelectionTurnstile = 'true';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Turnstile failed to load.'));
      document.head.appendChild(script);
    });
    return scriptLoader;
  }

  onMount(() => {
    let widgetId: string | null = null;
    const sitekey = env.PUBLIC_TURNSTILE_SITE_KEY;
    if (!sitekey) {
      message = 'The security check is not configured.';
      return;
    }

    loadScript()
      .then(() => {
        const api = turnstileWindow().turnstile;
        if (!api) throw new Error('Turnstile is unavailable.');
        message = '';
        widgetId = api.render(container, {
          sitekey,
          action,
          theme: 'auto',
          appearance: 'interaction-only',
          callback: (token: string) => onToken(token),
          'expired-callback': () => onToken(''),
          'error-callback': () => {
            onToken('');
            message = 'Unable to complete the security check. Please try again.';
          }
        });
      })
      .catch(() => {
        message = 'Unable to load the security check. Please refresh the page.';
      });

    return () => {
      const api = turnstileWindow().turnstile;
      if (widgetId && api) api.remove(widgetId);
      onToken('');
    };
  });
</script>

<div class="turnstile-wrap">
  <div bind:this={container}></div>
  {#if message}<p class="turnstile-message" role="status">{message}</p>{/if}
</div>

<style>
  .turnstile-wrap { margin-top: 14px; min-height: 30px; }
  .turnstile-message { margin: 0; color: #6b7280; font-size: 0.85rem; }
</style>
