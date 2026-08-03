-- Backend-only student credentials for recovery-code authentication.
-- Plaintext recovery codes and personal passwords are never stored here.
begin;

create table if not exists public.student_credentials (
  index_number varchar primary key
    references public.students(index_number) on delete cascade,
  recovery_code_hash text not null,
  recovery_code_fingerprint text not null unique,
  personal_password_hash text,
  password_version integer not null default 0 check (password_version >= 0),
  recovery_version integer not null default 1 check (recovery_version >= 1),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  password_changed_at timestamptz,
  recovery_rotated_at timestamptz not null default now()
);

create table if not exists public.student_password_challenges (
  token_hash text primary key,
  index_number varchar not null
    references public.students(index_number) on delete cascade,
  recovery_version integer not null,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists student_password_challenges_expiry
  on public.student_password_challenges (expires_at);
create index if not exists student_password_challenges_student
  on public.student_password_challenges (index_number, consumed_at, expires_at desc);

alter table public.student_credentials enable row level security;
alter table public.student_credentials force row level security;
alter table public.student_password_challenges enable row level security;
alter table public.student_password_challenges force row level security;

revoke all on table public.student_credentials
  from public, anon, authenticated;
revoke all on table public.student_password_challenges
  from public, anon, authenticated;
grant select, insert, update, delete on table public.student_credentials
  to service_role;
grant select, insert, update, delete on table public.student_password_challenges
  to service_role;

-- Consume a password-setup challenge and update the password atomically.
create or replace function public.consume_student_password_challenge(
  p_token_hash text,
  p_password_hash text
)
returns table(index_number varchar, password_version integer)
language plpgsql
security invoker
set search_path = pg_catalog, public
as $$
declare
  challenge public.student_password_challenges%rowtype;
begin
  delete from public.student_password_challenges
  where expires_at < now() - interval '1 day';

  select * into challenge
  from public.student_password_challenges
  where token_hash = p_token_hash
  for update;

  if not found
     or challenge.consumed_at is not null
     or challenge.expires_at <= now()
     or not exists (
       select 1 from public.student_credentials credentials
       where credentials.index_number = challenge.index_number
         and credentials.recovery_version = challenge.recovery_version
     ) then
    return;
  end if;

  update public.student_password_challenges
  set consumed_at = now()
  where token_hash = p_token_hash;

  return query
  update public.student_credentials credentials
  set personal_password_hash = p_password_hash,
      password_version = credentials.password_version + 1,
      password_changed_at = now(),
      updated_at = now()
  where credentials.index_number = challenge.index_number
    and credentials.recovery_version = challenge.recovery_version
  returning credentials.index_number, credentials.password_version;
end;
$$;

revoke all on function public.consume_student_password_challenge(text, text)
  from public, anon, authenticated;
grant execute on function public.consume_student_password_challenge(text, text)
  to service_role;

alter table public.student_auth_requests
  drop constraint if exists student_auth_requests_request_type_check;
alter table public.student_auth_requests
  add constraint student_auth_requests_request_type_check
  check (request_type in (
    'magic_link', 'password',
    'login', 'personal_login', 'recovery_verify', 'password_set', 'admin_login'
  ));

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
  v_now timestamptz := now();
begin
  if p_request_type not in (
    'login', 'personal_login', 'recovery_verify', 'password_set', 'admin_login'
  ) then
    raise exception 'Invalid authentication request type.';
  end if;

  perform pg_advisory_xact_lock(72150420260802);

  delete from public.student_auth_requests
  where created_at < v_now - interval '7 days';

  if (select count(*) from public.student_auth_requests
      where request_type = p_request_type
        and index_hash = p_index_hash
        and ip_hash = p_ip_hash
        and outcome = 'failed'
        and created_at >= v_now - interval '15 minutes') >= 5
    or (select count(*) from public.student_auth_requests
        where request_type = p_request_type
          and ip_hash = p_ip_hash
          and created_at >= v_now - interval '1 hour') >= 20 then
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

revoke all on function public.reserve_student_auth_request(text, text, text)
  from public, anon, authenticated;
grant execute on function public.reserve_student_auth_request(text, text, text)
  to service_role;

commit;

notify pgrst, 'reload schema';

-- Verification: these return no browser grants or policies for credential tables.
select grantee, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and table_name in ('student_credentials', 'student_password_challenges')
  and grantee in ('PUBLIC', 'anon', 'authenticated')
order by table_name, grantee, privilege_type;

select schemaname, tablename, policyname, roles, cmd
from pg_policies
where schemaname = 'public'
  and tablename in ('student_credentials', 'student_password_challenges')
order by tablename, policyname;
