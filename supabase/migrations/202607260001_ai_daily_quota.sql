create table if not exists public.ai_daily_usage (
  user_id uuid not null,
  usage_date date not null,
  request_count integer not null default 0 check (request_count >= 0),
  updated_at timestamptz not null default now(),
  primary key (user_id, usage_date)
);

alter table public.ai_daily_usage enable row level security;

revoke all on table public.ai_daily_usage from anon, authenticated;

create or replace function public.consume_ai_daily_quota(
  p_user_id uuid,
  p_usage_date date,
  p_daily_limit integer default 10
)
returns table (
  allowed boolean,
  used_count integer,
  remaining_count integer
)
language plpgsql
security definer
set search_path = public
as $$
declare
  current_count integer;
begin
  if p_daily_limit < 1 then
    raise exception 'Daily limit must be greater than zero';
  end if;

  -- 同一用户同一天的并发请求串行处理，避免首次写入时产生竞争。
  perform pg_advisory_xact_lock(
    hashtextextended(p_user_id::text || ':' || p_usage_date::text, 0)
  );

  select request_count
    into current_count
    from public.ai_daily_usage
   where user_id = p_user_id
     and usage_date = p_usage_date
   for update;

  if not found then
    insert into public.ai_daily_usage (user_id, usage_date, request_count)
    values (p_user_id, p_usage_date, 1);

    return query select true, 1, greatest(p_daily_limit - 1, 0);
    return;
  end if;

  if current_count >= p_daily_limit then
    return query select false, current_count, 0;
    return;
  end if;

  current_count := current_count + 1;

  update public.ai_daily_usage
     set request_count = current_count,
         updated_at = now()
   where user_id = p_user_id
     and usage_date = p_usage_date;

  return query
    select true, current_count, greatest(p_daily_limit - current_count, 0);
end;
$$;

revoke all on function public.consume_ai_daily_quota(uuid, date, integer) from public;
revoke all on function public.consume_ai_daily_quota(uuid, date, integer) from anon;
revoke all on function public.consume_ai_daily_quota(uuid, date, integer) from authenticated;
grant execute on function public.consume_ai_daily_quota(uuid, date, integer) to service_role;

comment on table public.ai_daily_usage is
  'Server-only daily DeepSeek request counters. No client RLS policies by design.';
