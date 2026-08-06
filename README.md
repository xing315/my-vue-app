# my-vue-app

## A 股量化分析看板

“量化分析”页面是只读研究与决策辅助工具，不连接券商，也不执行交易。前端请求
`/api/quant/dashboard`；后端未启动时会展示带有醒目标识的演示快照，演示内容不可用于投资决策。

后端位于 `quant-service/`，启动方式见该目录的 README。首次使用 Supabase 持久化持仓前执行：

```sh
supabase db push
```

历史行情与特征应保存在后端 DuckDB/Parquet 中；Supabase 只保存用户持仓、自选与每日评分快照。

本地首次使用：

```sh
npm run quant:sync     # 首次下载全市场数据并生成评分，耗时较长
npm run quant:server   # 终端 1：启动分析 API
npm run dev            # 终端 2：启动网站
```

页面只有在真实快照生成成功后才会移除 `DEMO` 标记。

`npm run quant:sync` 会在本地快照通过安全门后自动发布到 Supabase；如果发布配置缺失或
发布失败，命令会以失败状态退出，不会只同步本地后假装成功。无需再单独执行发布命令。

## 智能投研驾驶舱

量化页默认展示个人驾驶舱。登录用户可跨设备同步自选股与持仓，查看盘后评分、Top 30、
均线和风险变化信号，并基于服务端可信数据生成 DeepSeek 研究简报。资讯页会使用股票代码或
公司全称进行精确关联，不使用模糊简称推断。

上线前执行最新迁移并重新部署两个 Edge Function：

```sh
supabase db push
supabase functions deploy financial-news
supabase functions deploy deepseek-chat
```

随后重新运行 `npm run quant:sync`。第一次新快照用于建立比较基线，从第二个交易日快照开始
产生评分、排名、均线和风险变化信号。预警仅在站内展示，不发送邮件、短信，也不连接券商。

## DeepSeek AI 问答

资讯页通过 Supabase Edge Function 调用 DeepSeek，API Key 不会进入浏览器代码。

首次部署时，在 Supabase 项目中设置 DeepSeek 密钥、网站所有者的 Supabase User ID，并部署函数：

```sh
supabase secrets set DEEPSEEK_API_KEY=你的密钥
supabase secrets set AI_ALLOWED_USER_ID=你的Supabase用户ID
supabase functions deploy deepseek-chat
```

User ID 可在 Supabase 控制台的 Authentication → Users 中找到。使用 UUID 格式的 User ID，
不要填写邮箱。函数会在服务端验证登录令牌，并只允许该 User ID 调用 DeepSeek。

## 每日 AI 配额

AI 每天最多调用 10 次，按 Asia/Shanghai（北京时间）的自然日重置。计数保存在
`ai_daily_usage` 表中，并通过服务端数据库函数原子更新，浏览器无法绕过。

部署函数前，需要先执行数据库迁移：

```sh
supabase db push
supabase functions deploy deepseek-chat
```

不要把真实 API Key 写入 `.env`、Vue 文件或提交到 Git。

This template should help get you started developing with Vue 3 in Vite.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Recommended Browser Setup

- Chromium-based browsers (Chrome, Edge, Brave, etc.):
  - [Vue.js devtools](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd) 
  - [Turn on Custom Object Formatter in Chrome DevTools](http://bit.ly/object-formatters)
- Firefox:
  - [Vue.js devtools](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [Turn on Custom Object Formatter in Firefox DevTools](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## Customize configuration

See [Vite Configuration Reference](https://vite.dev/config/).

## Project Setup

```sh
npm install
```

### Compile and Hot-Reload for Development

```sh
npm run dev
```

### Compile and Minify for Production

```sh
npm run build
```
