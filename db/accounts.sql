-- ICT Flux accounts: sign-ups, the free trial, Pro payments (Paystack) and daily use.
-- Run in the Supabase SQL editor (safe to re-run).

create table if not exists public.profiles (
  user_id        uuid primary key,
  email          text,
  name           text,
  avatar         text,
  created_at     timestamptz not null default now(),
  trial_ends_at  timestamptz,
  pro_until      timestamptz,
  last_seen_at   timestamptz,
  visits         integer not null default 0
);

-- Ensure all columns exist even if profiles table was previously created partially
alter table public.profiles add column if not exists email text;
alter table public.profiles add column if not exists name text;
alter table public.profiles add column if not exists avatar text;
alter table public.profiles add column if not exists created_at timestamptz not null default now();
alter table public.profiles add column if not exists trial_ends_at timestamptz;
alter table public.profiles add column if not exists pro_until timestamptz;
alter table public.profiles add column if not exists last_seen_at timestamptz;
alter table public.profiles add column if not exists visits integer not null default 0;

-- Drop foreign key constraint if it exists so imported accounts work smoothly
alter table public.profiles drop constraint if exists profiles_user_id_fkey;

alter table public.profiles enable row level security;

-- Allow users to read their own profile
drop policy if exists "Users can read own profile" on public.profiles;
create policy "Users can read own profile" on public.profiles for select using (auth.uid() = user_id);

create table if not exists public.payments (
  reference    text primary key,
  user_id      uuid not null,
  email        text,
  amount_kobo  integer not null,
  period       text not null,
  paid_at      timestamptz not null default now()
);
alter table public.payments enable row level security;

create table if not exists public.usage_days (
  user_id  uuid not null,
  day      date not null,
  hits     integer not null default 1,
  primary key (user_id, day)
);
alter table public.usage_days enable row level security;

-- Count visit RPC
create or replace function public.count_visit(uid uuid, d date) returns void
language plpgsql security definer as $$
begin
  insert into public.usage_days (user_id, day, hits) values (uid, d, 1)
  on conflict (user_id, day) do update set hits = public.usage_days.hits + 1;
  if found and (select hits from public.usage_days where user_id = uid and day = d) = 1 then
    update public.profiles set visits = visits + 1 where user_id = uid;
  end if;
end $$;

revoke execute on function public.count_visit(uuid, date) from public, anon, authenticated;
grant execute on function public.count_visit(uuid, date) to service_role;

-- Automatically sync any user signing up through Supabase Auth (Google, email) into profiles
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
begin
  if exists (select 1 from public.profiles where lower(email) = lower(new.email)) then
    update public.profiles
    set
      user_id = new.id,
      name = coalesce(public.profiles.name, new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', split_part(new.email, '@', 1)),
      avatar = coalesce(public.profiles.avatar, new.raw_user_meta_data->>'avatar_url', new.raw_user_meta_data->>'picture'),
      last_seen_at = now()
    where lower(email) = lower(new.email);
  else
    insert into public.profiles (user_id, email, name, avatar, created_at, trial_ends_at, visits, last_seen_at)
    values (
      new.id,
      new.email,
      coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', split_part(new.email, '@', 1)),
      coalesce(new.raw_user_meta_data->>'avatar_url', new.raw_user_meta_data->>'picture'),
      now(),
      now() + interval '7 days',
      1,
      now()
    )
    on conflict (user_id) do update set
      email = excluded.email,
      name = coalesce(public.profiles.name, excluded.name),
      last_seen_at = now();
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- Automatically detect & backfill anyone who signed in while changes were made
insert into public.profiles (user_id, email, name, avatar, created_at, trial_ends_at, visits, last_seen_at)
select
  au.id,
  au.email,
  coalesce(au.raw_user_meta_data->>'full_name', au.raw_user_meta_data->>'name', split_part(au.email, '@', 1)),
  coalesce(au.raw_user_meta_data->>'avatar_url', au.raw_user_meta_data->>'picture'),
  au.created_at,
  au.created_at + interval '7 days',
  1,
  now()
from auth.users au
where not exists (
  select 1 from public.profiles p where lower(p.email) = lower(au.email) or p.user_id = au.id
);
