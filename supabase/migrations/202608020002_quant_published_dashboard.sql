-- Published, read-only quant dashboard. Heavy history remains on the local Mac.
create table if not exists public.quant_market_snapshots (
  trade_date date primary key,
  updated_at timestamptz not null,
  model_version text not null,
  coverage_count integer not null check (coverage_count >= 0),
  eligible_count integer not null check (eligible_count >= 0),
  market jsonb not null,
  validation jsonb not null default '{}'::jsonb,
  sources jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.quant_latest_scores (
  symbol text primary key check (symbol ~ '^[036][0-9]{5}$'),
  name text not null,
  industry text not null default '未分类',
  score smallint not null check (score between 0 and 100),
  confidence smallint not null check (confidence between 0 and 100),
  rating text not null check (rating in ('重点研究','值得关注','中性观察','谨慎','回避','数据不足')),
  price numeric(16,4),
  change_percent numeric(10,4),
  position_min smallint not null default 0,
  position_max smallint not null default 0,
  excluded boolean not null default false,
  detail jsonb not null,
  trade_date date not null,
  updated_at timestamptz not null,
  model_version text not null
);

create index if not exists quant_latest_scores_rank_idx
  on public.quant_latest_scores (excluded, score desc, confidence desc);
create index if not exists quant_latest_scores_name_idx
  on public.quant_latest_scores (name);
create index if not exists quant_latest_scores_industry_idx
  on public.quant_latest_scores (industry, score desc);

alter table public.quant_market_snapshots enable row level security;
alter table public.quant_latest_scores enable row level security;

-- Published analysis contains no account information and is readable by the site.
create policy "public reads quant market snapshots" on public.quant_market_snapshots
  for select to anon, authenticated using (true);
create policy "public reads published quant scores" on public.quant_latest_scores
  for select to anon, authenticated using (true);

-- No browser write policy: only the local service_role key can publish.
