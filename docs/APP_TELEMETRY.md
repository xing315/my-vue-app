# App 埋点数据接入

本项目的 `App 观测` 页面读取 Supabase 表 `app_telemetry_events`，批量上报入口为：

```text
POST https://ohnnjrbutzbkmjcdbpxt.supabase.co/functions/v1/app-events
```

## 部署顺序

1. 将 `supabase/migrations/202607300001_app_telemetry_events.sql` 应用到 Supabase。
2. 部署 Edge Function：`app-events`。
3. 为函数设置随机的 `APP_TELEMETRY_INGEST_KEY`，App 通过 `X-Ingest-Key` 请求头携带同一个值。
4. 用户登录网站后进入“App 观测”页面查看数据。

函数使用 Supabase 自带的 `SUPABASE_URL` 和 `SUPABASE_SERVICE_ROLE_KEY` 写表。不要把
service role key 放进网页或 App。

## 请求格式

请求体兼容 MyStudy `ReportStore` 当前产生的 JSON 数组，单批最多 500 条：

```json
[
  {
    "type": "method",
    "timestamp": 1785400000000,
    "method": "com.example.OrderService#submit",
    "costMs": 42.6
  },
  {
    "type": "page_resume",
    "timestamp": 1785400001000,
    "page": "com.example.mystudy.MainActivity"
  }
]
```

建议同时发送以下请求头：

```text
Content-Type: application/json; charset=utf-8
X-Ingest-Key: <仅用于埋点接收的密钥>
X-App-Id: com.example.mystudy
X-App-Version: 1.0
X-Device-Id: <获得用户同意后生成的随机安装 ID>
X-Session-Id: <每次冷启动生成的随机 UUID>
```

支持的事件类型：`startup`、`method`、`page_resume`、`page_pause`、`click`、`block`、
`aop_enter`、`aop_exit`。旧版 `main_thread_block` 会在接口中自动归一化为 `block`。

成功响应为 HTTP 202：

```json
{
  "accepted": 2,
  "batchId": "1acde52f-a05c-48f0-90dc-2eea40b45ba0",
  "receivedAt": "2026-07-30T08:00:00.000Z"
}
```

生产环境启用前，应完成用户授权、字段脱敏、采样、保存期限、限流和密钥轮换。
