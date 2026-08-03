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

Students sign in with an index number and either `student123` for read-only access or their personal
password for editable access. First-time password creation and forgotten-password resets use the
permanent 16-digit recovery code distributed by the administrator. No email or Supabase browser Auth
is used.

## Student flow

- `/login` — student index and shared or personal password
- `/module-grades` — view or edit Fluid Mechanics and Mechanics grades
- `/preferences` — rank all ten departments from 1 to 10
- `/results` — module grades, GPA, rank, estimated allocation, confidence, cutoffs, and corrections
- `/fluid-mechanics` — compatibility redirect to `/module-grades`

When backend `STUDENT_WRITES_ENABLED=false`, every student write keeps the temporary unavailable
message. Recovery and personal-password authentication remain available for controlled testing.

## Verify

```powershell
npm.cmd test
npm.cmd run check
npm.cmd run build
```
