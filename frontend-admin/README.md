# Field Selection Frontend

SvelteKit student interface for module grades, field preferences, and live estimated allocation results.

## Setup

```powershell
npm.cmd install
npm.cmd run dev
```

Configure a local `.env`:

```env
PUBLIC_SUPABASE_URL=https://your-project.supabase.co
PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
PUBLIC_API_BASE_URL=http://localhost:8000
```

Students sign in with an index number that exists in the `students` table and the shared password `student123`.

## Student flow

- `/login` — student index and password
- `/module-grades` — save Fluid Mechanics and Mechanics grades
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
