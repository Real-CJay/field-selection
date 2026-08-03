# Recovery-code authentication deployment

Students use `student123` for read-only access. A personal password creates an editable 30-minute
session. First-time setup and password reset require the student's permanent 16-digit recovery code.
No plaintext password or recovery code is stored in Supabase, application logs, or browser storage.

## Backend variables

Keep these in Render only:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-secret-service-role-key
FRONTEND_URL=http://localhost:5173,https://field-selection-omega.vercel.app
AUTH_RATE_LIMIT_HMAC_KEY=use-a-long-random-secret-value
STUDENT_READONLY_PASSWORD=student123
STUDENT_READ_TOKEN_SECRET=use-a-different-random-secret-at-least-32-characters
STUDENT_EDIT_TOKEN_SECRET=use-a-separate-random-secret-at-least-32-characters
STUDENT_CREDENTIAL_PEPPER=use-a-random-secret-at-least-32-characters
STUDENT_WRITES_ENABLED=false
ADMIN_TOKEN_SECRET=use-another-random-secret-at-least-32-characters
ADMIN_USERNAME=CJay
ADMIN_PASSWORD=use-a-long-random-password
TRUST_PROXY_HEADERS=true
```

The frontend needs only `PUBLIC_API_BASE_URL`.

Back up `STUDENT_CREDENTIAL_PEPPER` securely. Changing or losing it invalidates every recovery code
and personal password; it must never be committed or exposed to the frontend.

## Database and code generation

1. Back up Supabase.
2. Apply `supabase/migrations/20260803133106_student_recovery_credentials.sql`.
3. Deploy the backend with `STUDENT_WRITES_ENABLED=false`.
4. Generate codes from the backend directory, choosing a new path outside the repository:

   ```powershell
   .\.venv\Scripts\python.exe .\generate_student_recovery_codes.py `
     --output "D:\Offline\field-selection.recovery-codes.csv"
   ```

5. Store the CSV offline and distribute each code only to its matching student. The command cannot
   reproduce existing plaintext codes.
6. Rotate one compromised or lost code with:

   ```powershell
   .\.venv\Scripts\python.exe .\generate_student_recovery_codes.py `
     --index 250544U `
     --output "D:\Offline\250544U.recovery-codes.csv"
   ```

Rotation preserves the personal password but invalidates outstanding setup challenges.

## Release order

1. Verify RLS and confirm `anon` and `authenticated` have no grants or policies on credential tables.
2. Deploy the frontend and test read-only login, personal login, recovery setup, and reset with test
   students while writes remain disabled.
3. Verify preferences, grades, and correction-request writes in a controlled environment with the
   flag enabled.
4. Set `STUDENT_WRITES_ENABLED=true` only after recovery codes are distributed.
5. Keep Supabase email signups disabled; this system does not use Supabase Auth.
