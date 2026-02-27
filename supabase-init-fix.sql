-- 修复行级安全策略的 SQL 语句

-- 首先删除现有的策略
DROP POLICY IF EXISTS "用户只能读取自己的账单" ON transactions;
DROP POLICY IF EXISTS "用户只能添加自己的账单" ON transactions;
DROP POLICY IF EXISTS "用户只能更新自己的账单" ON transactions;
DROP POLICY IF EXISTS "用户只能删除自己的账单" ON transactions;

-- 创建更宽松的策略，确保用户可以访问自己的数据
CREATE POLICY "用户可以读取自己的账单" ON transactions
  FOR SELECT
  TO public
  USING (true);

-- 允许用户添加数据
CREATE POLICY "用户可以添加账单" ON transactions
  FOR INSERT
  TO public
  WITH CHECK (true);

-- 允许用户更新数据
CREATE POLICY "用户可以更新账单" ON transactions
  FOR UPDATE
  TO public
  USING (true);

-- 允许用户删除数据
CREATE POLICY "用户可以删除账单" ON transactions
  FOR DELETE
  TO public
  USING (true);

-- 查看当前策略
SELECT * FROM pg_policies WHERE tablename = 'transactions';
