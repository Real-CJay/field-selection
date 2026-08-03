export type StudentAccessMode = 'read-only' | 'editable';

export interface StudentApiSession {
  accessMode: StudentAccessMode;
  token: string;
}

const SESSION_KEY = 'field-selection-api-session';
const LEGACY_READ_TOKEN_KEY = 'field-selection-read-token';

export function saveStudentApiSession(session: StudentApiSession): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  sessionStorage.removeItem(LEGACY_READ_TOKEN_KEY);
}

export function getStudentApiSession(): StudentApiSession | null {
  if (typeof sessionStorage === 'undefined') return null;
  const saved = sessionStorage.getItem(SESSION_KEY);
  if (saved) {
    try {
      const parsed = JSON.parse(saved) as Partial<StudentApiSession>;
      if (
        (parsed.accessMode === 'read-only' || parsed.accessMode === 'editable')
        && typeof parsed.token === 'string'
        && parsed.token.length > 0
      ) return parsed as StudentApiSession;
    } catch {
      // Invalid browser state is cleared below.
    }
    sessionStorage.removeItem(SESSION_KEY);
  }
  const legacy = sessionStorage.getItem(LEGACY_READ_TOKEN_KEY);
  if (!legacy) return null;
  const migrated = { accessMode: 'read-only' as const, token: legacy };
  saveStudentApiSession(migrated);
  return migrated;
}

export function clearStudentApiSession(): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(LEGACY_READ_TOKEN_KEY);
}

export async function getStudentApiToken(): Promise<string> {
  const session = getStudentApiSession();
  if (session) return session.token;
  throw new Error('Your secure session has expired. Please log in again.');
}

export async function getStudentEditToken(): Promise<string> {
  const session = getStudentApiSession();
  if (session?.accessMode === 'editable') return session.token;
  throw new Error('Editable student authentication is required.');
}

// Compatibility exports for older callers during deployment.
export function saveStudentReadToken(token: string): void {
  saveStudentApiSession({ accessMode: 'read-only', token });
}

export function getStudentReadToken(): string | null {
  const session = getStudentApiSession();
  return session?.accessMode === 'read-only' ? session.token : null;
}

export const clearStudentReadToken = clearStudentApiSession;
