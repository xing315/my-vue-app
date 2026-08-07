create table if not exists public.members (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 50),
  phone text not null check (phone ~ '^1[3-9][0-9]{9}$'),
  notes text not null default '' check (char_length(notes) <= 500),
  balance numeric(12,2) not null default 0 check (balance >= 0),
  total_recharged numeric(12,2) not null default 0 check (total_recharged >= 0),
  total_spent numeric(12,2) not null default 0 check (total_spent >= 0),
  visit_count integer not null default 0 check (visit_count >= 0),
  last_consumed_on date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, phone)
);

create table if not exists public.member_transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  member_id uuid not null references public.members(id) on delete cascade,
  transaction_type text not null check (transaction_type in ('recharge', 'consume', 'reversal')),
  amount numeric(12,2) not null check (amount > 0),
  balance_delta numeric(12,2) not null check (balance_delta <> 0),
  balance_before numeric(12,2) not null check (balance_before >= 0),
  balance_after numeric(12,2) not null check (balance_after >= 0),
  business_date date not null default current_date check (business_date <= current_date),
  note text not null default '' check (char_length(note) <= 500),
  original_transaction_id uuid references public.member_transactions(id),
  created_at timestamptz not null default now(),
  check ((transaction_type = 'reversal') = (original_transaction_id is not null))
);

create index if not exists members_user_last_visit_idx on public.members (user_id, last_consumed_on desc nulls last, created_at desc);
create index if not exists member_transactions_member_created_idx on public.member_transactions (member_id, created_at desc);
create index if not exists member_transactions_user_date_idx on public.member_transactions (user_id, business_date desc);
create unique index if not exists member_transactions_one_reversal_idx on public.member_transactions (original_transaction_id) where original_transaction_id is not null;

alter table public.members enable row level security;
alter table public.member_transactions enable row level security;

create policy "members_owner_all" on public.members for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "member_transactions_owner_read" on public.member_transactions for select to authenticated
  using (auth.uid() = user_id);

create or replace function public.create_member(
  p_name text, p_phone text, p_notes text default '', p_opening_amount numeric default 0, p_business_date date default current_date
) returns public.members
language plpgsql security definer set search_path = public
as $$
declare v_user uuid := auth.uid(); v_member public.members; v_amount numeric(12,2) := round(coalesce(p_opening_amount, 0), 2);
begin
  if v_user is null then raise exception '请先登录'; end if;
  if trim(coalesce(p_name, '')) = '' then raise exception '请输入会员姓名'; end if;
  if coalesce(p_phone, '') !~ '^1[3-9][0-9]{9}$' then raise exception '请输入正确的11位手机号'; end if;
  if v_amount < 0 then raise exception '首次充值不能小于0'; end if;
  if p_business_date > current_date then raise exception '业务日期不能晚于今天'; end if;
  insert into public.members (user_id, name, phone, notes, balance, total_recharged)
  values (v_user, trim(p_name), p_phone, trim(coalesce(p_notes, '')), v_amount, v_amount) returning * into v_member;
  if v_amount > 0 then
    insert into public.member_transactions(user_id, member_id, transaction_type, amount, balance_delta, balance_before, balance_after, business_date, note)
    values(v_user, v_member.id, 'recharge', v_amount, v_amount, 0, v_amount, p_business_date, '建档首次充值');
  end if;
  return v_member;
exception when unique_violation then raise exception '该手机号已是会员';
end;
$$;

create or replace function public.apply_member_transaction(
  p_member_id uuid, p_type text, p_amount numeric, p_business_date date default current_date, p_note text default ''
) returns public.members
language plpgsql security definer set search_path = public
as $$
declare v_user uuid := auth.uid(); v_member public.members; v_amount numeric(12,2) := round(p_amount, 2); v_after numeric(12,2);
begin
  if v_user is null then raise exception '请先登录'; end if;
  if p_type not in ('recharge', 'consume') then raise exception '不支持的业务类型'; end if;
  if v_amount is null or v_amount <= 0 then raise exception '金额必须大于0'; end if;
  if p_business_date > current_date then raise exception '业务日期不能晚于今天'; end if;
  select * into v_member from public.members where id = p_member_id and user_id = v_user for update;
  if not found then raise exception '会员不存在或无权操作'; end if;
  if p_type = 'consume' and v_member.balance < v_amount then raise exception '会员余额不足'; end if;
  v_after := v_member.balance + case when p_type = 'recharge' then v_amount else -v_amount end;
  update public.members set
    balance = v_after,
    total_recharged = total_recharged + case when p_type = 'recharge' then v_amount else 0 end,
    total_spent = total_spent + case when p_type = 'consume' then v_amount else 0 end,
    visit_count = visit_count + case when p_type = 'consume' then 1 else 0 end,
    last_consumed_on = case when p_type = 'consume' then greatest(coalesce(last_consumed_on, p_business_date), p_business_date) else last_consumed_on end,
    updated_at = now()
  where id = p_member_id returning * into v_member;
  insert into public.member_transactions(user_id, member_id, transaction_type, amount, balance_delta, balance_before, balance_after, business_date, note)
  values(v_user, p_member_id, p_type, v_amount, case when p_type = 'recharge' then v_amount else -v_amount end, v_member.balance - case when p_type = 'recharge' then v_amount else -v_amount end, v_member.balance, p_business_date, trim(coalesce(p_note, '')));
  return v_member;
end;
$$;

create or replace function public.reverse_member_transaction(p_transaction_id uuid, p_reason text)
returns public.members
language plpgsql security definer set search_path = public
as $$
declare v_user uuid := auth.uid(); v_tx public.member_transactions; v_member public.members; v_after numeric(12,2); v_last date;
begin
  if v_user is null then raise exception '请先登录'; end if;
  if char_length(trim(coalesce(p_reason, ''))) < 2 then raise exception '请填写冲正原因'; end if;
  select * into v_tx from public.member_transactions where id = p_transaction_id and user_id = v_user for update;
  if not found then raise exception '流水不存在或无权操作'; end if;
  if v_tx.transaction_type = 'reversal' then raise exception '冲正流水不能再次冲正'; end if;
  if exists(select 1 from public.member_transactions where original_transaction_id = v_tx.id) then raise exception '该流水已经冲正'; end if;
  select * into v_member from public.members where id = v_tx.member_id and user_id = v_user for update;
  if v_member.balance - v_tx.balance_delta < 0 then raise exception '当前余额不足，无法冲正该笔充值'; end if;
  v_after := v_member.balance - v_tx.balance_delta;
  insert into public.member_transactions(user_id, member_id, transaction_type, amount, balance_delta, balance_before, balance_after, business_date, note, original_transaction_id)
  values(v_user, v_member.id, 'reversal', v_tx.amount, -v_tx.balance_delta, v_member.balance, v_after, current_date, trim(p_reason), v_tx.id);
  if v_tx.transaction_type = 'consume' then
    select max(t.business_date) into v_last from public.member_transactions t
    where t.member_id = v_member.id and t.transaction_type = 'consume' and t.id <> v_tx.id
      and not exists(select 1 from public.member_transactions r where r.original_transaction_id = t.id);
  else v_last := v_member.last_consumed_on;
  end if;
  update public.members set
    balance = v_after,
    total_recharged = total_recharged - case when v_tx.transaction_type = 'recharge' then v_tx.amount else 0 end,
    total_spent = total_spent - case when v_tx.transaction_type = 'consume' then v_tx.amount else 0 end,
    visit_count = visit_count - case when v_tx.transaction_type = 'consume' then 1 else 0 end,
    last_consumed_on = v_last,
    updated_at = now()
  where id = v_member.id returning * into v_member;
  return v_member;
end;
$$;

revoke all on function public.create_member(text,text,text,numeric,date) from public;
revoke all on function public.apply_member_transaction(uuid,text,numeric,date,text) from public;
revoke all on function public.reverse_member_transaction(uuid,text) from public;
grant execute on function public.create_member(text,text,text,numeric,date) to authenticated;
grant execute on function public.apply_member_transaction(uuid,text,numeric,date,text) to authenticated;
grant execute on function public.reverse_member_transaction(uuid,text) to authenticated;
