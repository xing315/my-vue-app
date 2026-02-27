-- 在 Supabase SQL 编辑器中执行以下 SQL 语句创建表

-- 创建账单表
CREATE TABLE transactions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  date TEXT NOT NULL,
  person TEXT NOT NULL CHECK (person IN ('husband', 'wife')),
  amount float8 NOT NULL,
  category TEXT NOT NULL,
  description TEXT,
  user_id UUID NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 创建索引以提高查询性能
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_person ON transactions(person);
CREATE INDEX idx_transactions_category ON transactions(category);
CREATE INDEX idx_transactions_user_id ON transactions(user_id);

-- 启用行级安全策略（RLS）
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- 允许用户只能访问自己的数据
CREATE POLICY "用户只能读取自己的账单" ON transactions
  FOR SELECT
  TO public
  USING (user_id = auth.uid());

-- 允许用户只能添加自己的账单
CREATE POLICY "用户只能添加自己的账单" ON transactions
  FOR INSERT
  TO public
  WITH CHECK (user_id = auth.uid());

-- 允许用户只能更新自己的账单
CREATE POLICY "用户只能更新自己的账单" ON transactions
  FOR UPDATE
  TO public
  USING (user_id = auth.uid());

-- 允许用户只能删除自己的账单
CREATE POLICY "用户只能删除自己的账单" ON transactions
  FOR DELETE
  TO public
  USING (user_id = auth.uid());
