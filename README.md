# Field Selection

Student field-selection estimator with a SvelteKit frontend, FastAPI allocation service, and Supabase database.

## Backend

```powershell
cd Back_end_table_codes
python -m pip install -r requirements-dev.txt
uvicorn api_server:app --reload
```

The backend requires the variables listed in `Back_end_table_codes/.env.example`. Never place the service-role key, HMAC key, or session secrets in the frontend.

For the four-decimal database column, run `Back_end_table_codes/migrate_average_gpa_four_decimals.psql` in the Supabase SQL Editor before release. The API calculates GPA directly from the six module values, so allocation precision does not depend on previously stored two-decimal averages.

## Frontend

See `frontend-admin/README.md`.

## Student authentication

Students use their index number with `student123` for read-only access. A separately distributed,
permanent 16-digit recovery code creates or resets a personal password; personal-password sessions
can write preferences, Fluid/Mechanics grades, and grade-correction requests when the rollout flag is
enabled. The browser never connects to Supabase directly. See
[RECOVERY_CODE_DEPLOYMENT.md](RECOVERY_CODE_DEPLOYMENT.md) for the secure rollout procedure.
