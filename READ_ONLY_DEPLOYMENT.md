# Read-only deployment

Students sign in with their registered index number and the shared `student123` password. The
backend returns a short-lived signed token that permits reads for only that index number. Student
preferences, grades, and correction requests cannot be changed while editing is under development.

## Backend variables

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-secret-service-role-key
FRONTEND_URL=http://localhost:5173,https://field-selection-omega.vercel.app
AUTH_RATE_LIMIT_HMAC_KEY=use-a-long-random-secret-value
STUDENT_READONLY_PASSWORD=student123
STUDENT_READ_TOKEN_SECRET=use-a-different-random-secret-at-least-32-characters
ADMIN_TOKEN_SECRET=use-another-random-secret-at-least-32-characters
ADMIN_USERNAME=CJay
ADMIN_PASSWORD=use-a-long-random-password
TRUST_PROXY_HEADERS=true
```

Keep every secret in Render. The frontend needs only `PUBLIC_API_BASE_URL`.

## Database lockdown

Run `supabase/migrations/20260803094520_disable_student_browser_writes.sql` in the Supabase SQL Editor before
deploying. It preserves data and service-role access while removing browser-role access and student
write policies. Disable new email signups in Supabase Authentication settings because this version
does not use Supabase Auth or send authentication email.

## Deployment order

1. Back up Supabase and run the read-only lockdown SQL.
2. Deploy the FastAPI backend.
3. Deploy the Svelte frontend.
4. Verify student and administrator login, read-only views, and blocked student writes.
5. Remove obsolete Supabase publishable-key, callback, Turnstile, and maintenance-preview variables.
