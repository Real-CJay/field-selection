# Secure student authentication deployment

Application code does not contain Brevo credentials. Brevo is only the SMTP transport configured inside Supabase.

## 1. Lock down the exposed database immediately

In the Supabase SQL Editor, run `Back_end_table_codes/security_incident_lockdown.psql` first. This removes all browser-role access while keeping service-role backend access available. It intentionally makes the old deployed frontend unusable until the matching backend/frontend are deployed.

Do not run `Back_end_table_codes/emergency_lockdown_public_schema.psql`; it is an older untracked draft and is not part of this rollout.

After the emergency script, inspect its two verification result sets:

- the grant query must return no rows for `anon` or `authenticated`;
- every public table must show `rls_enabled = true`.

Because there was a suspected incident, also replace the Render admin password with a unique password of at least 16 characters. Rotate the Supabase secret/service key, Turnstile secret, Brevo SMTP key, and HMAC/session secrets if any of them were ever pasted into a public issue, chat, log, screenshot, browser bundle, or commit. Do not rotate a database key until the replacement has been installed in the backend, or the backend will stop working.

## 2. Back up and apply the complete migration

Take a Supabase database backup before changing ownership links or history. Then run these files in order:

1. `Back_end_table_codes/audit_and_enforce_student_uniqueness.psql`
2. `Back_end_table_codes/migrate_average_gpa_four_decimals.psql`
3. `Back_end_table_codes/create_student_preferences_history.psql`
4. `Back_end_table_codes/secure_student_auth_rls.psql`

The second migration intentionally stops if the same non-empty registered email belongs to multiple students. Resolve those duplicates before retrying it. It then:

- adds the unique Auth ownership link;
- creates the HMAC-only authentication request audit table;
- removes old policies from the protected student tables;
- leaves anonymous roles with no database access;
- permits authenticated students to change only their own preferences and Fluid/Mechanics grades.

Read-only access now goes through FastAPI using a short-lived, index-bound signed token. Registered emails, admin data, cohort data, and student records are never read directly by an anonymous browser database role.

The uniqueness migration first copies any duplicate preference rows to the locked `private` schema, then retains the newest preference row per index. The secure migration will stop instead of guessing if duplicate student, result, preference, or registered-email identities remain. Review the backup and verification output before continuing.

## 3. Configure Brevo SMTP

In Brevo:

1. Verify the Gmail sender that will send Field Selection messages.
2. Create an SMTP key and copy the SMTP login and key once.
3. Disable click tracking for transactional messages so authentication links are not rewritten.

In Supabase Dashboard, open Authentication email/SMTP settings and enable custom SMTP:

- Host: `smtp-relay.brevo.com`
- Port: `587`
- Username: the Brevo SMTP login
- Password: the Brevo SMTP key
- Sender name: `Field Selection`
- Sender email: the verified Gmail sender

Keep these SMTP values only in Supabase. Do not add them to GitHub, Vercel, Render, or `.env` files.

In the Supabase Magic Link email template, keep the link target as `{{ .ConfirmationURL }}`.

## 4. Configure Supabase Auth redirects

Set the production site URL to `https://field-selection-omega.vercel.app` and allow both redirect URLs:

- `https://field-selection-omega.vercel.app/auth/callback`
- `http://localhost:5173/auth/callback`

## 5. Configure Cloudflare Turnstile

Create a Turnstile widget for the production Vercel hostname. Use Cloudflare's documented testing keys for localhost development, or add the local hostname if supported by the selected widget configuration.

Store the site key in the frontend and the secret key only in the backend. The backend validates every token with Siteverify and checks the `student-auth` action.

## 6. Backend variables

Configure these in Render and in `Back_end_table_codes/.env` for local testing:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
FRONTEND_URL=http://localhost:5173,https://field-selection-omega.vercel.app
FRONTEND_AUTH_CALLBACK_URL=https://field-selection-omega.vercel.app/auth/callback
TURNSTILE_SECRET_KEY=your-turnstile-secret
TURNSTILE_ALLOWED_HOSTNAMES=field-selection-omega.vercel.app
AUTH_RATE_LIMIT_HMAC_KEY=a-long-random-secret
STUDENT_READONLY_PASSWORD=configure-the-shared-read-only-password
STUDENT_READ_TOKEN_SECRET=a-separate-random-secret-at-least-32-characters
ADMIN_TOKEN_SECRET=another-random-secret-at-least-32-characters
ANONYMOUS_LOOKUP_MIN_GROUP_SIZE=3
TRUST_PROXY_HEADERS=false
ENABLE_API_DOCS=false
MAINTENANCE_MODE=true
MAINTENANCE_PREVIEW_INDEXES=250314P,250544U
```

Use `http://localhost:5173/auth/callback` for `FRONTEND_AUTH_CALLBACK_URL` while testing the local frontend. Generate `AUTH_RATE_LIMIT_HMAC_KEY` as an independent random secret; do not reuse any Supabase, Brevo, admin, or Turnstile credential.

## 7. Frontend variables

Configure these in Vercel and in `frontend-admin/.env` locally:

```env
PUBLIC_SUPABASE_URL=https://your-project.supabase.co
PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
PUBLIC_API_BASE_URL=https://your-backend.example.com
PUBLIC_MAINTENANCE_MODE=true
PUBLIC_TURNSTILE_SITE_KEY=your-turnstile-site-key
```

Only variables prefixed with `PUBLIC_` reach the browser. Never put service-role, SMTP, HMAC, or Turnstile secret values in them.

## 8. Verify before expanding access

Keep maintenance enabled and test only `250314P` and `250544U`:

1. Confirm `student123` can read but cannot save any student change.
2. Request a magic link and confirm the response never displays the registered email.
3. Follow the link, create an eight-character-or-longer password, and save pending preferences.
4. Log out, return with the personal password, and change preferences.
5. Verify Fluid/Mechanics changes and correction submissions also require the Supabase session.
6. Verify one preview student cannot alter the other student's rows.
7. Inspect Brevo delivery, Supabase Auth, `student_auth_requests`, preference history, and correction history.
8. Confirm Civil Engineering reports 125 seats and total capacity is 753.
9. Confirm the public Supabase REST API returns no student, result, preference, history, audit, or admin data when called with only the publishable key.

Do not disable maintenance as part of this rollout. Expanding access should be a later, staged change that remains below the configured 280 daily send ceiling.
