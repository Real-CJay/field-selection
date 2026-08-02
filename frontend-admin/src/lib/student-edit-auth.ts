import type { SupabaseClient } from '@supabase/supabase-js';
import { supabase } from './supabase';

type EmailLookup = (indexNumber: string) => Promise<string | null>;

export type StudentEditAuthResult =
  | { ok: true }
  | { ok: false; message: string };

function normalizeIndexNumber(indexNumber: string): string {
  return indexNumber.trim().toUpperCase();
}

async function emailForIndex(indexNumber: string, lookup: EmailLookup): Promise<string> {
  const email = await lookup(normalizeIndexNumber(indexNumber));
  if (!email) throw new Error('Index number not found in the student registry.');
  return email;
}

export async function signInWithPersonalPassword(
  indexNumber: string,
  password: string,
  lookup: EmailLookup,
  client: SupabaseClient = supabase
): Promise<StudentEditAuthResult> {
  try {
    const email = await emailForIndex(indexNumber, lookup);
    const { error } = await client.auth.signInWithPassword({ email, password });
    if (error) return { ok: false, message: 'Invalid index number or personal password.' };
    return { ok: true };
  } catch {
    return { ok: false, message: 'Unable to sign in. Please try again.' };
  }
}

export async function sendPreferenceOtp(
  indexNumber: string,
  lookup: EmailLookup,
  client: SupabaseClient = supabase
): Promise<StudentEditAuthResult> {
  try {
    const email = await emailForIndex(indexNumber, lookup);
    const { error } = await client.auth.signInWithOtp({ email });
    if (error) return { ok: false, message: 'Unable to send the verification code. Please try again.' };
    return { ok: true };
  } catch {
    return { ok: false, message: 'Unable to send the verification code. Please try again.' };
  }
}

export async function verifyPreferenceOtp(
  indexNumber: string,
  otp: string,
  lookup: EmailLookup,
  client: SupabaseClient = supabase
): Promise<StudentEditAuthResult> {
  try {
    const email = await emailForIndex(indexNumber, lookup);
    const { error: otpError } = await client.auth.verifyOtp({ email, token: otp, type: 'email' });
    if (otpError) return { ok: false, message: 'That verification code is invalid or has expired.' };

    return { ok: true };
  } catch {
    return { ok: false, message: 'Unable to verify the code. Please try again.' };
  }
}

export async function hasEditableSession(
  indexNumber: string,
  lookup: EmailLookup,
  client: SupabaseClient = supabase
): Promise<boolean> {
  try {
    const [email, userResponse] = await Promise.all([
      emailForIndex(indexNumber, lookup),
      client.auth.getUser()
    ]);
    return !userResponse.error && userResponse.data.user?.email?.toLowerCase() === email.toLowerCase();
  } catch {
    return false;
  }
}

export async function signOutStudentAuth(client: SupabaseClient = supabase): Promise<void> {
  await client.auth.signOut();
}
