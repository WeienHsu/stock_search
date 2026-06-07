-- Enable Row Level Security (RLS) on all base tables in the public schema.
--
-- Why:
--   Supabase auto-created tables default to "Unrestricted" (RLS disabled).
--   Enabling RLS is the recommended baseline: it is "deny by default", so even
--   if the anon key leaks or a client ever connects directly, no rows are
--   exposed without an explicit policy.
--
-- Impact on this app:
--   The backend connects directly via DATABASE_URL using the Supabase `postgres`
--   role, which has BYPASSRLS. Enabling RLS does NOT affect these direct
--   connections. No policies are added here, so anon/authenticated access stays
--   fully closed (which is intended -- this app does not use the Supabase REST
--   API / anon key).
--
-- Run: paste into Supabase Dashboard -> SQL Editor, or psql against DATABASE_URL.

DO $$
DECLARE
  t record;
BEGIN
  FOR t IN
    SELECT tablename
    FROM pg_tables
    WHERE schemaname = 'public'
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY;', t.tablename);
  END LOOP;
END $$;
