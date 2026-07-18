import { createClient } from '@supabase/supabase-js';
import { PUBLIC_SUPABASE_PUBLISHABLE_KEY, PUBLIC_SUPABASE_URL } from '$env/static/public';

if (!PUBLIC_SUPABASE_URL || !PUBLIC_SUPABASE_PUBLISHABLE_KEY) {
  throw new Error('Supabase environment variables are not configured.');
}

export const supabase = createClient(PUBLIC_SUPABASE_URL, PUBLIC_SUPABASE_PUBLISHABLE_KEY);
