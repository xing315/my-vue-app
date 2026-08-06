-- Personal research cockpit: alert preferences, auditable market signals and saved news.
create table if not exists public.quant_alert_rules (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text check (symbol is null or symbol ~ '^[036][0-9]{5}$'),
  rule_type text not null check (rule_type in ('score_threshold','score_change','top30_change','ma_break','risk_change','holding_downgrade','related_news')),
  threshold numeric,
  enabled boolean not null default true,
  created_at timestamptz not null default now(),
  unique (user_id, symbol, rule_type)
);

create table if not exists public.quant_signal_events (
  id uuid primary key default gen_random_uuid(),
  trade_date date not null,
  symbol text not null check (symbol ~ '^[036][0-9]{5}$'),
  signal_type text not null,
  severity text not null default 'info' check (severity in ('info','attention','risk')),
  title text not null,
  reason text not null,
  previous_value jsonb,
  current_value jsonb,
  evidence jsonb not null default '{}'::jsonb,
  source text not null default '盘后量化流水线',
  created_at timestamptz not null default now(),
  unique (trade_date, symbol, signal_type)
);

create table if not exists public.quant_user_alerts (
  user_id uuid not null references auth.users(id) on delete cascade,
  signal_id uuid not null references public.quant_signal_events(id) on delete cascade,
  read_at timestamptz,
  created_at timestamptz not null default now(),
  primary key (user_id, signal_id)
);

create table if not exists public.quant_saved_news (
  user_id uuid not null references auth.users(id) on delete cascade,
  news_id text not null,
  title text not null,
  url text,
  source text not null,
  published_at timestamptz,
  related_symbols text[] not null default '{}',
  created_at timestamptz not null default now(),
  primary key (user_id, news_id)
);

create index if not exists quant_signal_events_date_idx on public.quant_signal_events (trade_date desc, severity, symbol);
create index if not exists quant_user_alerts_unread_idx on public.quant_user_alerts (user_id, created_at desc) where read_at is null;

alter table public.quant_alert_rules enable row level security;
alter table public.quant_signal_events enable row level security;
alter table public.quant_user_alerts enable row level security;
alter table public.quant_saved_news enable row level security;

create policy "users manage own alert rules" on public.quant_alert_rules
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "authenticated users read quant signals" on public.quant_signal_events
  for select to authenticated using (true);
create policy "users manage own alert inbox" on public.quant_user_alerts
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "users manage own saved news" on public.quant_saved_news
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Market signals and inbox fan-out are written only by the service role.
revoke insert, update, delete on public.quant_signal_events from anon, authenticated;

