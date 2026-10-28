-- ICT Flux: the last finished scan (so the app loads instantly) and the phones that get app notifications.
-- Run once in the Supabase SQL editor (safe to re-run). Only the server (service key) uses it.

create table if not exists scan_snapshots (
  name        text primary key,
  body        text not null,
  updated_at  timestamptz not null default now()
);
alter table scan_snapshots enable row level security;

-- Phones that turned on notifications in the app (Web Push). One row per phone/browser.
create table if not exists push_subscriptions (
  endpoint    text primary key,
  p256dh      text not null,
  auth        text not null,
  created_at  timestamptz not null default now()
);
alter table push_subscriptions enable row level security;

-- Which trades a phone hears about: 'aplus' (A+ only), 'a' (A+ and A, the default) or 'b' (A+, A, B and the heads-ups).
alter table push_subscriptions add column if not exists tier text not null default 'a';
