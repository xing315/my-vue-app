-- 修复行级安全策略

-- 首先禁用 RLS 测试
ALTER TABLE transactions DISABLE ROW LEVEL SECURITY;

-- 测试插入权限
INSERT INTO transactions (date, person, amount, category, description, user_id)
VALUES ('2026-02-27', '丈夫', 100, '餐饮', '测试', '430cd2a8-80e9-4a36-9b47-9d55f62b73a4');

-- 重新启用 RLS
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;

-- 创建更宽松的策略
CREATE POLICY "允许所有认证用户读取" ON transactions
  FOR SELECT
  TO authenticated
  USING (true);

CREATE POLICY "允许所有认证用户插入" ON transactions
  FOR INSERT
  TO authenticated
  WITH CHECK (true);

CREATE POLICY "允许所有认证用户更新" ON transactions
  FOR UPDATE
  TO authenticated
  USING (true);

CREATE POLICY "允许所有认证用户删除" ON transactions
  FOR DELETE
  TO authenticated
  USING (true);

-- 查看当前策略
SELECT * FROM pg_policies WHERE tablename = 'transactions';
