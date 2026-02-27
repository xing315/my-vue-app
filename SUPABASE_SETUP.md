# 家庭记账应用 - Supabase 集成配置指南

## 概述
本应用已成功集成 Supabase 数据库，用于存储家庭记账数据，并添加了用户认证功能。

## 配置步骤

### 1. 创建 Supabase 项目
1. 访问 [Supabase 官网](https://supabase.com/)
2. 注册或登录账号
3. 点击 "New Project" 创建新项目
4. 填写项目信息：
   - Name: 家庭记账（或任意名称）
   - Database Password: 设置强密码
   - Region: 选择最近的区域
5. 等待项目创建完成（通常需要 1-2 分钟）

### 2. 获取 API 密钥
1. 进入项目仪表板
2. 点击左侧菜单的 "Settings" → "API"
3. 复制以下信息：
   - **Project URL**: 例如 `https://xxxxx.supabase.co`
   - **anon public**: 例如 `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 3. 配置环境变量
打开项目根目录的 `.env` 文件，填入你的 Supabase 凭证：

```env
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your-anon-key-here
```

### 4. 启用用户认证
1. 在 Supabase 仪表板中，点击左侧菜单的 "Authentication"
2. 点击 "Settings" 标签
3. 在 "Site URL" 中输入：`http://localhost:5173`
4. 在 "Redirect URLs" 中输入：`http://localhost:5173`
5. 保存设置

### 5. 创建数据库表
1. 在 Supabase 仪表板中，点击左侧菜单的 "SQL Editor"
2. 点击 "New query"
3. 复制并执行项目根目录 `supabase-init.sql` 文件中的 SQL 语句

### 6. 重启开发服务器
由于修改了 `.env` 文件，Vite 会自动重启服务器。如果没有自动重启，请手动重启：

```bash
# 停止当前服务器（Ctrl+C）
# 重新启动
npm run dev
```

## 验证配置

1. 访问 http://127.0.0.1:5173/
2. 点击顶部导航栏的"登录/注册"
3. 注册一个新账号
4. 登录后，点击"家庭记账"
5. 尝试添加一条支出记录
6. 如果成功添加，说明 Supabase 集成成功
7. 可以在 Supabase 仪表板的 "Table Editor" 中查看数据

## 功能特性

### 已实现的功能
- ✅ 用户注册和登录
- ✅ 添加支出记录（日期、人员、金额、分类、描述）
- ✅ 删除支出记录
- ✅ 查看所有支出记录
- ✅ 按日期范围筛选
- ✅ 按人员筛选
- ✅ 统计总支出
- ✅ 按人员统计支出
- ✅ 按分类统计支出
- ✅ 按日期统计支出
- ✅ 清空所有数据
- ✅ 数据持久化到 Supabase
- ✅ 数据隔离（每个用户只能看到自己的数据）

### 数据存储
- 所有数据存储在 Supabase PostgreSQL 数据库中
- 使用 `transactions` 表存储账单记录
- 使用 Supabase Auth 存储用户信息
- 支持实时数据同步

## 技术栈
- **前端框架**: Vue 3
- **构建工具**: Vite
- **数据库**: Supabase (PostgreSQL)
- **认证**: Supabase Auth
- **UI**: 自定义 CSS（渐变背景、卡片式布局）

## 常见问题

### Q: 提示"添加失败，请检查网络连接和 Supabase 配置"
A: 请检查：
1. `.env` 文件中的 URL 和 Key 是否正确
2. 网络连接是否正常
3. Supabase 项目是否已创建并激活
4. 数据库表是否已创建
5. 用户是否已登录

### Q: 数据没有保存到数据库
A: 请检查：
1. Supabase 仪表板中的 "Table Editor" 是否能看到表
2. 行级安全策略是否已启用
3. 浏览器控制台是否有错误信息
4. 用户是否已登录（需要用户ID才能保存数据）

### Q: 如何查看数据库中的数据
A: 
1. 登录 Supabase 仪表板
2. 点击左侧菜单的 "Table Editor"
3. 选择 `transactions` 表查看数据

### Q: 如何查看用户信息
A: 
1. 登录 Supabase 仪表板
2. 点击左侧菜单的 "Authentication"
3. 查看用户列表

## 安全建议

⚠️ **重要提示**：
- 本示例使用了宽松的 RLS 策略，允许所有公开访问
- 在生产环境中，建议：
  - 完善行级安全策略，确保用户只能访问自己的数据
  - 使用 HTTPS 协议
  - 定期备份数据库
  - 实现密码复杂度要求
  - 添加邮箱验证功能

## 下一步优化建议

1. **邮箱验证**: 启用邮箱验证功能
2. **密码重置**: 添加忘记密码功能
3. **数据导出**: 支持导出为 Excel 或 CSV
4. **图表展示**: 使用 Chart.js 或 ECharts 添加可视化图表
5. **预算管理**: 添加月度预算设置和提醒
6. **数据备份**: 定期备份数据库
7. **多设备同步**: 支持多个设备访问同一账户
8. **深色模式**: 添加深色主题支持

## 联系支持

如有问题，请参考：
- [Supabase 官方文档](https://supabase.com/docs)
- [Vue 3 官方文档](https://vuejs.org/)
