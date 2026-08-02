import type { StudentRankings } from './types';

export const PASSWORD_SETUP_INDEX_KEY = 'field-selection-password-setup-index';
const PENDING_PREFERENCES_KEY = 'field-selection-pending-preferences';
const PENDING_LIFETIME_MS = 60 * 60 * 1000;

export function markPasswordSetup(indexNumber: string): void {
  localStorage.setItem(PASSWORD_SETUP_INDEX_KEY, indexNumber.trim().toUpperCase());
}

export function clearPasswordSetup(): void {
  localStorage.removeItem(PASSWORD_SETUP_INDEX_KEY);
}

export function isPasswordSetupPending(indexNumber: string): boolean {
  return localStorage.getItem(PASSWORD_SETUP_INDEX_KEY) === indexNumber.trim().toUpperCase();
}

export function savePendingPreferences(indexNumber: string, rankings: StudentRankings): void {
  localStorage.setItem(PENDING_PREFERENCES_KEY, JSON.stringify({
    indexNumber: indexNumber.trim().toUpperCase(),
    rankings,
    expiresAt: Date.now() + PENDING_LIFETIME_MS
  }));
}

export function readPendingPreferences(indexNumber: string): StudentRankings | null {
  const saved = localStorage.getItem(PENDING_PREFERENCES_KEY);
  if (!saved) return null;
  try {
    const parsed = JSON.parse(saved) as {
      indexNumber?: string;
      rankings?: StudentRankings;
      expiresAt?: number;
    };
    if (
      parsed.indexNumber !== indexNumber.trim().toUpperCase()
      || typeof parsed.expiresAt !== 'number'
      || parsed.expiresAt < Date.now()
      || !parsed.rankings
    ) {
      localStorage.removeItem(PENDING_PREFERENCES_KEY);
      return null;
    }
    return parsed.rankings;
  } catch {
    localStorage.removeItem(PENDING_PREFERENCES_KEY);
    return null;
  }
}

export function clearPendingPreferences(): void {
  localStorage.removeItem(PENDING_PREFERENCES_KEY);
}
