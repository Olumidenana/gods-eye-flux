-- ICT Flux invite-only access: run once in the Supabase SQL editor (safe to re-run).
-- Add a row per person in Table Editor -> access_codes:
--   code        what they type to get in (letters, numbers and dashes, e.g. TUNDE-OCT)
--   name        who it is for (shown to them as "Welcome, ...")
--   expires_at  when their access ends (leave empty for no end date)
--   enabled     untick to switch someone off at once
-- Only the server (service key) can read this table.

create table if not exists access_codes (
  code          text primary key check (code ~ '^[A-Za-z0-9-]{3,40}$'),
  name          text not null default '',
  plan          text not null default 'pro',
  expires_at    timestamptz,
  enabled       boolean not null default true,
  note          text,
  created_at    timestamptz not null default now(),
  last_seen_at  timestamptz
);
alter table access_codes enable row level security;

-- which code an always-on enrollment belongs to (its bot stops when that code ends)
alter table autotrade_users add column if not exists access_code text;
