-- 彻底修复 transactions 表的行级安全策略

-- 1. 查看当前 RLS 状态
SELECT 
    relname as table_name,
    relrowsecurity as rls_enabled,
    relforcerowsecurity as rls_forced
FROM pg_class 
WHERE relname = 'transactions';

-- 2. 查看当前所有策略
SELECT 
    policyname as policy_name,
    permissive as is_permissive,
    roles,
    cmd as operation,
    qual as using_expression,
    with_check as check_expression
FROM pg_policies 
WHERE tablename = 'transactions';

-- 3. 删除所有现有策略
DROP POLICY IF EXISTS "用户只能读取自己的账单" ON transactions;
DROP POLICY IF EXISTS "用户只能添加自己的账单" ON transactions;
DROP POLICY IF EXISTS "用户只能更新自己的账单" ON transactions;
DROP POLICY IF EXISTS "用户只能删除自己的账单" ON transactions;
DROP POLICY IF EXISTS "允许认证用户读取所有账单" ON transactions;
DROP POLICY IF EXISTS "允许认证用户添加账单" ON transactions;
DROP POLICY IF EXISTS "允许认证用户更新账单" ON transactions;
DROP POLICY IF EXISTS "允许认证用户删除账单" ON transactions;

-- 4. 临时禁用 RLS（用于快速测试）
ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;

-- 5. 创建最简单的策略 - 允许所有认证用户进行所有操作
CREATE POLICY "允许所有认证用户操作" ON transactions
  FOR ALL
  TO authenticated
  USING (true)
  WITH CHECK (true);

-- 6. 重新启用 RLS
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- 7. 验证策略已创建
SELECT * FROM pg_policies WHERE tablename = 'transactions';

-- 8. 测试插入（可选）
-- INSERT INTO transactions (date, person, amount, category, description, user_id)
-- VALUES (CURRENT_DATE, '测试', 1.00, '测试', 'RLS修复测试', '00000000-0000-0000-0000-000000000000');
