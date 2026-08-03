# Field Selection Frontend

SvelteKit student interface for module grades, field preferences, and live estimated allocation results.

## Setup

```powershell
npm.cmd install
npm.cmd run dev
```

Configure a local `.env`:

```env
PUBLIC_API_BASE_URL=http://localhost:8000
```

Students sign in with an index number that exists in the `students` table and the shared password
`student123`. Every student session is read-only. Preference, grade, and correction changes display a
temporary unavailable message and do not write data.

## Student flow

- `/login` — student index and password
- `/module-grades` — view or enter Fluid Mechanics and Mechanics grades; saving is temporarily disabled
- `/preferences` — rank all ten departments from 1 to 10
- `/results` — module grades, four-decimal GPA, rank, estimated allocation, confidence, and cutoffs
- `/fluid-mechanics` — compatibility redirect to `/module-grades`

Saving preferences redirects to `/results`. The allocation request may take 50–60 seconds while a sleeping Render backend starts.

## Verify

```powershell
npm.cmd test
npm.cmd run check
npm.cmd run build
```
