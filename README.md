# my-vue-app

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
