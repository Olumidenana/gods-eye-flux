-- ICT Flux always-on auto-trading: run once in the Supabase SQL editor.
-- Row Level Security is on with no policies, so only the server (service key) can read
-- or write these tables; the public/anon key cannot see anything.

create table if not exists autotrade_users (
  id                 uuid primary key default gen_random_uuid(),
  created_at         timestamptz not null default now(),
  token_enc          text not null,              -- Deriv API token, encrypted (Fernet, AUTOTRADE_KEY)
  account_id         text not null,
  account_type       text not null check (account_type in ('demo', 'real')),
  currency           text not null default 'USD',
  risk_pct           numeric not null default 1.0,
  max_trades_day     int not null default 2,
  max_open           int not null default 3,
  day_loss_pct       numeric not null default 2.0,
  classes            text[] not null default '{forex,metal,index}',
  enabled            boolean not null default true,
  manage_hash        text not null,              -- sha256 of the user's manage key
  terms_version      text not null,
  accepted_terms_at  timestamptz not null,
  real_confirmed_at  timestamptz,
  day                text,                       -- NY trading day of day_start_balance
  day_start_balance  numeric,
  paused_reason      text
);

create table if not exists autotrade_log (
  id           bigserial primary key,
  created_at   timestamptz not null default now(),
  user_id      uuid not null references autotrade_users(id) on delete cascade,
  kind         text not null,                    -- enrolled | placed | skipped | error | updated | managed | claimed
  message      text not null,
  signal_id    text,
  market       text,
  contract_id  text
);
create index if not exists autotrade_log_user on autotrade_log (user_id, created_at desc);
create index if not exists autotrade_log_signal on autotrade_log (user_id, signal_id);

-- added later: per-user quality filters (safe to re-run)
alter table autotrade_users add column if not exists min_rr numeric not null default 2.0;
alter table autotrade_users add column if not exists min_grade text not null default 'B';

-- a trade is claimed before it is placed, so a plan found twice (the minute run and the 5-minute run, or two cron hits) is entered once.
-- This makes the claim atomic (safe to re-run); without it the claim is write-then-read-back, which still never double-enters.
create unique index if not exists autotrade_log_claim on autotrade_log (user_id, signal_id) where kind = 'claimed';

alter table autotrade_users enable row level security;
alter table autotrade_log enable row level security;
