# Secure student authentication deployment

Application code does not contain Brevo credentials. Brevo is only the SMTP transport configured inside Supabase.

## 1. Back up and apply SQL

Take a Supabase database backup before changing grants or policies. In the Supabase SQL Editor, run these files in order:

1. `Back_end_table_codes/create_student_preferences_history.psql`
2. `Back_end_table_codes/secure_student_auth_rls.psql`

The second migration intentionally stops if the same non-empty registered email belongs to multiple students. Resolve those duplicates before retrying it. It then:

- adds the unique Auth ownership link;
- creates the HMAC-only authentication request audit table;
- removes old policies from the protected student tables;
- keeps only the requested anonymous read access;
- permits authenticated students to change only their own preferences and Fluid/Mechanics grades.

Do not run `emergency_lockdown_public_schema.psql` for this rollout. It is the older blanket-lockdown approach and is not compatible with the read-only portal.

The older `audit_and_enforce_student_uniqueness.psql` and `migrate_average_gpa_four_decimals.psql` are separate data/schema migrations. If they are still outstanding, review their audit output and backup requirements independently rather than combining them with this authentication rollout.

## 2. Configure Brevo SMTP

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

## 3. Configure Supabase Auth redirects

Set the production site URL to `https://field-selection-omega.vercel.app` and allow both redirect URLs:

- `https://field-selection-omega.vercel.app/auth/callback`
- `http://localhost:5173/auth/callback`

## 4. Configure Cloudflare Turnstile

Create a Turnstile widget for the production Vercel hostname. Use Cloudflare's documented testing keys for localhost development, or add the local hostname if supported by the selected widget configuration.

Store the site key in the frontend and the secret key only in the backend. The backend validates every token with Siteverify and checks the `student-auth` action.

## 5. Backend variables

Configure these in Render and in `Back_end_table_codes/.env` for local testing:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
SUPABASE_PUBLISHABLE_KEY=your-publishable-key
FRONTEND_URL=http://localhost:5173,https://field-selection-omega.vercel.app
FRONTEND_AUTH_CALLBACK_URL=https://field-selection-omega.vercel.app/auth/callback
TURNSTILE_SECRET_KEY=your-turnstile-secret
AUTH_RATE_LIMIT_HMAC_KEY=a-long-random-secret
MAINTENANCE_MODE=true
MAINTENANCE_PREVIEW_INDEXES=250314P,250544U
```

Use `http://localhost:5173/auth/callback` for `FRONTEND_AUTH_CALLBACK_URL` while testing the local frontend. Generate `AUTH_RATE_LIMIT_HMAC_KEY` as an independent random secret; do not reuse any Supabase, Brevo, admin, or Turnstile credential.

## 6. Frontend variables

Configure these in Vercel and in `frontend-admin/.env` locally:

```env
PUBLIC_SUPABASE_URL=https://your-project.supabase.co
PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
PUBLIC_API_BASE_URL=https://your-backend.example.com
PUBLIC_MAINTENANCE_MODE=true
PUBLIC_TURNSTILE_SITE_KEY=your-turnstile-site-key
```

Only variables prefixed with `PUBLIC_` reach the browser. Never put service-role, SMTP, HMAC, or Turnstile secret values in them.

## 7. Verify before expanding access

Keep maintenance enabled and test only `250314P` and `250544U`:

1. Confirm `student123` can read but cannot save any student change.
2. Request a magic link and confirm the response never displays the registered email.
3. Follow the link, create an eight-character-or-longer password, and save pending preferences.
4. Log out, return with the personal password, and change preferences.
5. Verify Fluid/Mechanics changes and correction submissions also require the Supabase session.
6. Verify one preview student cannot alter the other student's rows.
7. Inspect Brevo delivery, Supabase Auth, `student_auth_requests`, preference history, and correction history.
8. Confirm Civil Engineering reports 125 seats and total capacity is 753.

Do not disable maintenance as part of this rollout. Expanding access should be a later, staged change that remains below the configured 280 daily send ceiling.
