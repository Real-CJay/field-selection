# Field Selection

Student field-selection estimator with a SvelteKit frontend, FastAPI allocation service, and Supabase database.

## Backend

```powershell
cd Back_end_table_codes
python -m pip install -r requirements-dev.txt
uvicorn api_server:app --reload
```

The backend requires `SUPABASE_URL` and a server-only `SUPABASE_KEY`. Never place the service-role key in the frontend.

For the four-decimal database column, run `Back_end_table_codes/migrate_average_gpa_four_decimals.psql` in the Supabase SQL Editor before release. The API calculates GPA directly from the six module values, so allocation precision does not depend on previously stored two-decimal averages.

## Frontend

See `frontend-admin/README.md`.
