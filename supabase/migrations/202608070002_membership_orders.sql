create table if not exists public.membership_products (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  sku text not null,
  name text not null check (char_length(trim(name)) between 1 and 60),
  variant text not null default '',
  category text not null default '烤鸭',
  price numeric(12,2) not null check (price >= 0),
  image_url text not null default '/images/members/roast-duck-menu.png',
  active boolean not null default true,
  sort_order integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, sku)
);

create table if not exists public.member_transaction_items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  transaction_id uuid not null references public.member_transactions(id) on delete cascade,
  product_id uuid references public.membership_products(id) on delete set null,
  product_name text not null,
  variant text not null default '',
  unit_price numeric(12,2) not null check (unit_price >= 0),
  quantity integer not null check (quantity between 1 and 99),
  line_total numeric(12,2) generated always as (unit_price * quantity) stored,
  created_at timestamptz not null default now()
);

create index if not exists membership_products_user_active_idx on public.membership_products(user_id, active, sort_order);
create index if not exists member_transaction_items_tx_idx on public.member_transaction_items(transaction_id);
create index if not exists member_transaction_items_product_idx on public.member_transaction_items(user_id, product_id);

alter table public.membership_products enable row level security;
alter table public.member_transaction_items enable row level security;
create policy "membership_products_owner_all" on public.membership_products for all to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "member_transaction_items_owner_read" on public.member_transaction_items for select to authenticated
  using (auth.uid() = user_id);

create or replace function public.ensure_default_membership_products()
returns setof public.membership_products
language plpgsql security definer set search_path = public
as $$
declare v_user uuid := auth.uid();
begin
  if v_user is null then raise exception '请先登录'; end if;
  insert into public.membership_products(user_id, sku, name, variant, category, price, sort_order)
  values
    (v_user, 'duck-half', '果木烤鸭', '半只', '烤鸭', 58, 10),
    (v_user, 'duck-whole', '果木烤鸭', '一只', '烤鸭', 108, 20),
    (v_user, 'duck-double', '果木烤鸭宴', '两只', '套餐', 198, 30),
    (v_user, 'pancake', '荷叶饼', '一套', '配菜', 8, 40),
    (v_user, 'sauce', '秘制甜面酱', '一份', '配菜', 6, 50)
  on conflict(user_id, sku) do nothing;
  return query select * from public.membership_products where user_id = v_user order by sort_order, created_at;
end;
$$;

create or replace function public.apply_member_order(
  p_member_id uuid, p_items jsonb, p_business_date date default current_date, p_note text default ''
) returns public.members
language plpgsql security definer set search_path = public
as $$
declare
  v_user uuid := auth.uid(); v_member public.members; v_tx_id uuid := gen_random_uuid();
  v_total numeric(12,2); v_after numeric(12,2); v_requested integer; v_valid integer;
begin
  if v_user is null then raise exception '请先登录'; end if;
  if p_business_date > current_date then raise exception '业务日期不能晚于今天'; end if;
  if jsonb_typeof(p_items) <> 'array' or jsonb_array_length(p_items) = 0 then raise exception '请至少选择一件菜品'; end if;
  select count(*) into v_requested from jsonb_to_recordset(p_items) as x(product_id uuid, quantity integer) where quantity between 1 and 99;
  select count(*), round(sum(p.price * x.quantity), 2) into v_valid, v_total
  from jsonb_to_recordset(p_items) as x(product_id uuid, quantity integer)
  join public.membership_products p on p.id = x.product_id and p.user_id = v_user and p.active
  where x.quantity between 1 and 99;
  if v_requested <> jsonb_array_length(p_items) or v_valid <> v_requested then raise exception '订单中包含无效或已下架菜品'; end if;
  if v_total is null or v_total <= 0 then raise exception '订单金额必须大于0'; end if;
  select * into v_member from public.members where id = p_member_id and user_id = v_user for update;
  if not found then raise exception '会员不存在或无权操作'; end if;
  if v_member.balance < v_total then raise exception '会员余额不足'; end if;
  v_after := v_member.balance - v_total;
  insert into public.member_transactions(id,user_id,member_id,transaction_type,amount,balance_delta,balance_before,balance_after,business_date,note)
  values(v_tx_id,v_user,v_member.id,'consume',v_total,-v_total,v_member.balance,v_after,p_business_date,trim(coalesce(p_note,'')));
  insert into public.member_transaction_items(user_id,transaction_id,product_id,product_name,variant,unit_price,quantity)
  select v_user,v_tx_id,p.id,p.name,p.variant,p.price,x.quantity
  from jsonb_to_recordset(p_items) as x(product_id uuid, quantity integer)
  join public.membership_products p on p.id=x.product_id and p.user_id=v_user and p.active;
  update public.members set balance=v_after,total_spent=total_spent+v_total,visit_count=visit_count+1,
    last_consumed_on=greatest(coalesce(last_consumed_on,p_business_date),p_business_date),updated_at=now()
  where id=v_member.id returning * into v_member;
  return v_member;
end;
$$;

revoke all on function public.ensure_default_membership_products() from public;
revoke all on function public.apply_member_order(uuid,jsonb,date,text) from public;
grant execute on function public.ensure_default_membership_products() to authenticated;
grant execute on function public.apply_member_order(uuid,jsonb,date,text) to authenticated;
