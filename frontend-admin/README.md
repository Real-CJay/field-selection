# Field Selection Frontend

Simple SvelteKit student interface for logging in and submitting nine field preferences to Supabase.

## Setup

```bash
npm install
npm run dev
```

The local `.env` contains the supplied Supabase project URL and publishable key. For another environment, configure:

```env
PUBLIC_SUPABASE_URL=https://your-project.supabase.co
PUBLIC_SUPABASE_PUBLISHABLE_KEY=your-publishable-key
```

Students sign in with an index number that exists in the `students` table and the shared password `student123`.

## Current pages

- `/login` — student index and password
- `/preferences` — rank all nine departments from 1 to 9

The result page and allocation integration are intentionally deferred.

## Verify

```bash
npm test
npm run check
npm run build
```
