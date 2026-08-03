const READ_TOKEN_KEY = 'field-selection-read-token';

export function saveStudentReadToken(token: string): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.setItem(READ_TOKEN_KEY, token);
}

export function getStudentReadToken(): string | null {
  if (typeof sessionStorage === 'undefined') return null;
  return sessionStorage.getItem(READ_TOKEN_KEY);
}

export function clearStudentReadToken(): void {
  if (typeof sessionStorage === 'undefined') return;
  sessionStorage.removeItem(READ_TOKEN_KEY);
}

export async function getStudentApiToken(): Promise<string> {
  const readToken = getStudentReadToken();
  if (readToken) return readToken;
  throw new Error('Your secure session has expired. Please log in again.');
}
