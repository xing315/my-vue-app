-- Personal A-share research state. Market history stays in DuckDB/Parquet.
create table if not exists public.quant_holdings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null check (symbol ~ '^[036][0-9]{5}$'),
  name text not null,
  cost numeric(14,4) not null check (cost > 0),
  shares integer not null check (shares > 0 and shares % 100 = 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.quant_watchlist (
  user_id uuid not null references auth.users(id) on delete cascade,
  symbol text not null check (symbol ~ '^[036][0-9]{5}$'),
  created_at timestamptz not null default now(),
  primary key (user_id, symbol)
);

create table if not exists public.quant_daily_scores (
  trade_date date not null,
  symbol text not null,
  model_version text not null,
  score smallint not null check (score between 0 and 100),
  confidence smallint not null check (confidence between 0 and 100),
  rating text not null check (rating in ('重点研究','值得关注','中性观察','谨慎','回避','数据不足')),
  dimensions jsonb not null,
  reasons jsonb not null,
  source_as_of jsonb not null,
  excluded boolean not null default false,
  exclusion_reasons jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  primary key (trade_date, symbol, model_version)
);

alter table public.quant_holdings enable row level security;
alter table public.quant_watchlist enable row level security;
alter table public.quant_daily_scores enable row level security;

create policy "users manage own quant holdings" on public.quant_holdings
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "users manage own quant watchlist" on public.quant_watchlist
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "authenticated users read daily scores" on public.quant_daily_scores
  for select to authenticated using (true);

create index if not exists quant_daily_scores_symbol_date_idx
  on public.quant_daily_scores (symbol, trade_date desc);
create index if not exists quant_daily_scores_rank_idx
  on public.quant_daily_scores (trade_date desc, score desc) where excluded = false;
