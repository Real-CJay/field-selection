import type { SupabaseClient } from '@supabase/supabase-js';
import { supabase } from './supabase';
import { getAuthenticatedStudent, type StudentIdentity } from './student-auth-client';
import { clearStudentReadToken } from './student-api-session';

type IdentityLookup = (accessToken: string) => Promise<StudentIdentity>;

export async function hasEditableSession(
  indexNumber: string,
  client: SupabaseClient = supabase,
  identityLookup: IdentityLookup = getAuthenticatedStudent
): Promise<boolean> {
  try {
    const sessionResponse = await client.auth.getSession();
    const accessToken = sessionResponse.data.session?.access_token;
    if (sessionResponse.error || !accessToken) return false;
    const [userResponse, identity] = await Promise.all([
      client.auth.getUser(accessToken),
      identityLookup(accessToken)
    ]);
    return !userResponse.error
      && Boolean(userResponse.data.user)
      && identity.index_number.trim().toUpperCase() === indexNumber.trim().toUpperCase();
  } catch {
    return false;
  }
}

export async function signOutStudentAuth(client: SupabaseClient = supabase): Promise<void> {
  clearStudentReadToken();
  await client.auth.signOut();
}
