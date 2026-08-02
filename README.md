# Field Selection

Student field-selection estimator with a SvelteKit frontend, FastAPI allocation service, and Supabase database.

## Backend

```powershell
cd Back_end_table_codes
python -m pip install -r requirements-dev.txt
uvicorn api_server:app --reload
```

The backend requires the variables listed in `Back_end_table_codes/.env.example`. Never place the service-role key, Turnstile secret, HMAC key, or SMTP credentials in the frontend.

For the four-decimal database column, run `Back_end_table_codes/migrate_average_gpa_four_decimals.psql` in the Supabase SQL Editor before release. The API calculates GPA directly from the six module values, so allocation precision does not depend on previously stored two-decimal averages.

## Frontend

See `frontend-admin/README.md`.

## Secure student editing

Shared-password access remains read-only. Preference changes, Fluid/Mechanics grade changes, and grade-correction requests require a verified Supabase Auth session. See [AUTH_DEPLOYMENT.md](AUTH_DEPLOYMENT.md) for the required SQL, Brevo SMTP, Supabase Auth, Turnstile, Render, and Vercel configuration.
