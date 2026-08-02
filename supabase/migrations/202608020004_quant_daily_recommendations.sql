create table if not exists public.quant_daily_recommendations (
  trade_date date not null,
  rank smallint not null check (rank between 1 and 30),
  symbol text not null check (symbol ~ '^[036][0-9]{5}$'),
  name text not null,
  industry text not null default '未分类',
  score smallint not null check (score between 0 and 100),
  confidence smallint not null check (confidence between 0 and 100),
  previous_rank smallint,
  rank_change smallint,
  price numeric(16,4),
  change_percent numeric(10,4),
  position_min smallint not null default 0,
  position_max smallint not null default 0,
  explanation jsonb not null,
  model_version text not null,
  experimental boolean not null default true,
  created_at timestamptz not null default now(),
  primary key (trade_date, rank, model_version),
  unique (trade_date, symbol, model_version)
);

create index if not exists quant_daily_recommendations_latest_idx
  on public.quant_daily_recommendations (trade_date desc, rank);

alter table public.quant_daily_recommendations enable row level security;
create policy "public reads daily quant recommendations"
  on public.quant_daily_recommendations for select to anon, authenticated using (true);

-- Browser writes are intentionally absent; only the local secret-key publisher writes.
