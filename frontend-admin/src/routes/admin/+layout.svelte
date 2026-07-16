<script lang="ts">
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { apiMode } from '$lib/api/client';
  import { apiLogs, clearSession, session } from '$lib/stores';

  let { children } = $props();
  let menuOpen = $state(false);

  const nav = [
    { href: '/admin', label: 'Overview', icon: '⌂' },
    { href: '/admin/imports', label: 'Data imports', icon: '⇧' },
    { href: '/admin/allocation', label: 'Allocation run', icon: '◇' },
    { href: '/admin/results', label: 'Results', icon: '≡' },
    { href: '/admin/api-log', label: 'API activity', icon: '↔' }
  ];

  onMount(() => { if (!$session) goto('/login', { replaceState: true }); });
  const active = (href: string) => href === '/admin' ? page.url.pathname === href : page.url.pathname.startsWith(href);
  function logout() { clearSession(); goto('/login'); }
</script>

<div class="admin-shell">
  <aside class:open={menuOpen}>
    <a class="brand" href="/admin" onclick={() => (menuOpen = false)}><span>FS</span><div><strong>FieldSelect</strong><small>Admin console</small></div></a>
    <p class="nav-title">Workspace</p>
    <nav aria-label="Administration">
      {#each nav as item}
        <a href={item.href} class:active={active(item.href)} onclick={() => (menuOpen = false)}><i>{item.icon}</i>{item.label}{#if item.href === '/admin/api-log' && $apiLogs.length}<b>{$apiLogs.length}</b>{/if}</a>
      {/each}
    </nav>
    <div class="side-bottom">
      <div class="environment"><span></span><div><strong>{apiMode === 'mock' ? 'Mock environment' : 'Backend connected'}</strong><small>{apiMode === 'mock' ? 'Safe fictional data' : 'Live HTTP requests'}</small></div></div>
      <button onclick={logout}><i>↗</i> Sign out</button>
    </div>
  </aside>

  {#if menuOpen}<button class="scrim" aria-label="Close navigation" onclick={() => (menuOpen = false)}></button>{/if}

  <div class="content">
    <header>
      <button class="menu-button" onclick={() => (menuOpen = true)} aria-label="Open navigation">☰</button>
      <div class="breadcrumb"><span>Field Selection</span><b>/</b><strong>{nav.find((item) => active(item.href))?.label ?? 'Admin'}</strong></div>
      <div class="admin-user"><div><strong>{$session?.admin.name ?? 'Administrator'}</strong><small>{$session?.admin.email ?? 'Mock session'}</small></div><span>SA</span></div>
    </header>
    <main>{@render children()}</main>
  </div>
</div>

<style>
  .admin-shell { min-height: 100vh; }
  aside { position: fixed; z-index: 50; inset: 0 auto 0 0; display: flex; width: 245px; flex-direction: column; border-right: 1px solid #273856; background: #17243e; padding: 25px 17px 19px; color: #fff; }
  .brand { display: flex; align-items: center; gap: 11px; padding: 0 9px; color: #fff; text-decoration: none; }
  .brand > span { display: grid; width: 37px; height: 37px; place-items: center; border-radius: 10px; background: #fff; color: #25447d; font-size: .61rem; font-weight: 800; }
  .brand strong, .brand small { display: block; }
  .brand strong { font-family: 'Manrope'; font-size: .92rem; }
  .brand small { margin-top: 2px; color: #8797b5; font-size: .57rem; letter-spacing: .08em; text-transform: uppercase; }
  .nav-title { margin: 42px 12px 10px; color: #697b9c; font-size: .58rem; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; }
  nav { display: grid; gap: 4px; }
  nav a { display: flex; align-items: center; gap: 11px; border-radius: 9px; padding: 11px 12px; color: #aab5ca; font-size: .76rem; font-weight: 600; text-decoration: none; transition: 150ms; }
  nav a:hover { background: rgba(255,255,255,.05); color: #fff; }
  nav a.active { background: #2a3d61; color: #fff; box-shadow: inset 3px 0 #75a5ff; }
  nav i { display: grid; width: 21px; place-items: center; font-style: normal; font-size: .92rem; }
  nav b { margin-left: auto; border-radius: 99px; background: #41639f; padding: 2px 6px; font-size: .55rem; }
  .side-bottom { margin-top: auto; }
  .environment { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; border: 1px solid #2b3d5b; border-radius: 10px; background: #1d2d49; padding: 11px; }
  .environment > span { width: 8px; height: 8px; border-radius: 50%; background: #50cca0; box-shadow: 0 0 0 4px rgba(80,204,160,.1); }
  .environment strong, .environment small { display: block; }
  .environment strong { font-size: .64rem; }
  .environment small { margin-top: 3px; color: #7f90ad; font-size: .56rem; }
  .side-bottom button { display: flex; width: 100%; align-items: center; gap: 10px; border: 0; border-radius: 9px; background: transparent; padding: 10px 12px; color: #94a2ba; cursor: pointer; font-size: .7rem; }
  .side-bottom button:hover { background: rgba(255,255,255,.05); color: #fff; }
  .side-bottom i { font-style: normal; }
  .content { min-height: 100vh; margin-left: 245px; }
  header { display: flex; height: 67px; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--line); background: #fff; padding: 0 36px; }
  .breadcrumb { display: flex; align-items: center; gap: 9px; color: #929cad; font-size: .69rem; }
  .breadcrumb b { color: #c3cad5; }
  .breadcrumb strong { color: #4f5d75; }
  .admin-user { display: flex; align-items: center; gap: 10px; text-align: right; }
  .admin-user strong, .admin-user small { display: block; }
  .admin-user strong { font-size: .68rem; }
  .admin-user small { margin-top: 2px; color: #8e98aa; font-size: .57rem; }
  .admin-user > span { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 10px; background: var(--blue-soft); color: var(--blue); font-size: .6rem; font-weight: 800; }
  .menu-button { display: none; border: 0; background: transparent; color: var(--navy); cursor: pointer; font-size: 1.25rem; }
  .scrim { position: fixed; z-index: 40; inset: 0; border: 0; background: rgba(10,18,34,.5); }
  @media (max-width: 860px) { aside { transform: translateX(-100%); transition: transform 180ms ease; } aside.open { transform: translateX(0); } .content { margin-left: 0; } header { padding: 0 18px; } .menu-button { display: block; } .breadcrumb { display: none; } }
  @media (max-width: 480px) { .admin-user div { display: none; } }
</style>
