import { browser } from '$app/environment';
import { writable } from 'svelte/store';
import type { ApiLogEntry, LoginResponse } from './types';

const SESSION_KEY = 'fieldselect_mock_session';

function initialSession(): LoginResponse | null {
  if (!browser) return null;
  const value = sessionStorage.getItem(SESSION_KEY);
  if (!value) return null;
  try {
    return JSON.parse(value) as LoginResponse;
  } catch {
    sessionStorage.removeItem(SESSION_KEY);
    return null;
  }
}

export const session = writable<LoginResponse | null>(initialSession());
export const apiLogs = writable<ApiLogEntry[]>([]);

export function saveSession(value: LoginResponse) {
  if (browser) sessionStorage.setItem(SESSION_KEY, JSON.stringify(value));
  session.set(value);
}

export function clearSession() {
  if (browser) sessionStorage.removeItem(SESSION_KEY);
  session.set(null);
}

export function addApiLog(entry: ApiLogEntry) {
  apiLogs.update((items) => [entry, ...items].slice(0, 100));
}

export function clearApiLogs() {
  apiLogs.set([]);
}
