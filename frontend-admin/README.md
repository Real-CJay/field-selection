# FieldSelect Admin Frontend

An isolated SvelteKit + TypeScript admin console for testing a field-selection backend. It starts in mock mode and uses fictional records only.

## Run locally

```bash
npm install
npm run dev
```

Open the local URL printed by Vite and use:

- Email: `admin@fieldselect.test`
- Password: `admin123`

## Available workflows

- Dashboard metrics, capacity utilisation, and recent operations
- Student, result, and preference CSV validation/import previews
- Allocation readiness, confirmation, execution, and outcome summary
- Searchable, filterable, paginated result audit with details and CSV export
- Simulated API request/response inspector
- Temporary session-based login and responsive admin navigation

No files from the repository's student-data archive are imported or exposed by this frontend.

## Connect the real backend

Copy `.env.example` to `.env` and set:

```env
PUBLIC_API_MODE=http
PUBLIC_API_BASE_URL=http://localhost:8000
```

Update endpoint paths or response mapping in `src/lib/api/http.ts` after the backend contract is available. Page components depend only on the shared `FieldSelectionApi` interface, so they do not need to be redesigned.

## Verify

```bash
npm run test
npm run check
npm run build
```

For a manual end-to-end pass: sign in, validate a test CSV, import valid rows, run an allocation, inspect/filter results, export CSV, and confirm each request appears in API Activity.
