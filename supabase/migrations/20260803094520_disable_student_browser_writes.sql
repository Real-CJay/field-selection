-- Keep all field-selection data behind the FastAPI service-role client.
-- This migration is idempotent and does not delete records, Auth users, or history.
begin;

create table if not exists public.student_auth_requests (
  id bigint generated always as identity primary key,
  index_hash text not null,
  ip_hash text not null,
  request_type text not null,
  outcome text not null default 'failed',
  created_at timestamptz not null default now(),
  constraint student_auth_requests_outcome_check
    check (outcome in ('failed', 'success', 'sent')),
  constraint student_auth_requests_request_type_check
    check (request_type in ('magic_link', 'login', 'password', 'admin_login'))
);

create index if not exists student_auth_requests_index_time
  on public.student_auth_requests (index_hash, request_type, outcome, created_at desc);
create index if not exists student_auth_requests_ip_time
  on public.student_auth_requests (ip_hash, request_type, outcome, created_at desc);

create table if not exists public.admin_action_audit (
  id bigint generated always as identity primary key,
  admin_username text not null,
  action text not null,
  target text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists admin_action_audit_created_at
  on public.admin_action_audit (created_at desc);

create or replace function public.reserve_student_auth_request(
  p_index_hash text,
  p_ip_hash text,
  p_request_type text
)
returns bigint
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
declare
  request_id bigint;
  current_time timestamptz := now();
begin
  if p_request_type not in ('login', 'admin_login') then
    raise exception 'Invalid authentication request type.';
  end if;

  perform pg_advisory_xact_lock(72150420260802);

  delete from public.student_auth_requests
  where created_at < current_time - interval '7 days';

  if (select count(*) from public.student_auth_requests
      where request_type = p_request_type
        and index_hash = p_index_hash
        and ip_hash = p_ip_hash
        and outcome = 'failed'
        and created_at >= current_time - interval '15 minutes') >= 5
    or (select count(*) from public.student_auth_requests
        where request_type = p_request_type
          and ip_hash = p_ip_hash
          and created_at >= current_time - interval '1 hour') >= 20 then
    raise exception 'AUTH_RATE_LIMIT' using errcode = 'P0001';
  end if;

  insert into public.student_auth_requests (
    index_hash, ip_hash, request_type, outcome
  ) values (
    p_index_hash, p_ip_hash, p_request_type, 'failed'
  ) returning id into request_id;

  return request_id;
end;
$$;

do $$
declare
  table_record record;
  policy_record record;
begin
  for table_record in
    select tablename from pg_tables where schemaname = 'public'
  loop
    execute format('alter table public.%I enable row level security', table_record.tablename);
  end loop;

  for policy_record in
    select schemaname, tablename, policyname
    from pg_policies
    where schemaname = 'public'
  loop
    execute format(
      'drop policy if exists %I on %I.%I',
      policy_record.policyname,
      policy_record.schemaname,
      policy_record.tablename
    );
  end loop;
end;
$$;

revoke all privileges on all tables in schema public from public, anon, authenticated;
revoke all privileges on all sequences in schema public from public, anon, authenticated;
revoke execute on all functions in schema public from public, anon, authenticated;

alter default privileges for role postgres in schema public
  revoke all privileges on tables from public, anon, authenticated;
alter default privileges for role postgres in schema public
  revoke all privileges on sequences from public, anon, authenticated;
alter default privileges for role postgres in schema public
  revoke execute on functions from public, anon, authenticated;

do $$
begin
  if to_regnamespace('private') is not null then
    execute 'revoke all privileges on schema private from anon, authenticated';
  end if;
end;
$$;

grant all privileges on all tables in schema public to service_role;
grant all privileges on all sequences in schema public to service_role;
grant execute on all functions in schema public to service_role;

commit;

notify pgrst, 'reload schema';

-- Verification: these queries should return no browser-role grants or policies.
select grantee, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('PUBLIC', 'anon', 'authenticated')
order by table_name, grantee, privilege_type;

select schemaname, tablename, policyname, roles, cmd
from pg_policies
where schemaname = 'public'
order by tablename, policyname;
