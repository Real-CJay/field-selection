import { supabase } from './supabase';

let readToken: string | null = null;

export function saveStudentReadToken(token: string): void {
  readToken = token;
}

export function getStudentReadToken(): string | null {
  return readToken;
}

export function clearStudentReadToken(): void {
  readToken = null;
}

export async function getStudentApiToken(): Promise<string> {
  const sessionResponse = await supabase.auth.getSession();
  const accessToken = sessionResponse.data.session?.access_token;
  if (!sessionResponse.error && accessToken) return accessToken;
  const readToken = getStudentReadToken();
  if (readToken) return readToken;
  throw new Error('Your secure session has expired. Please log in again.');
}
