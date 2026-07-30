<script>
import Home from './Home.vue'
import Accounting from './Accounting.vue'
import Auth from './Auth.vue'
import Download from './Download.vue'
import Blog from './Blog.vue'
import News from './News.vue'
import Analytics from './Analytics.vue'
import Toolkit from './Toolkit.vue'
import { supabase } from './supabase.js'

export default {
  components: { Home, Accounting, Auth, Download, Blog, News, Analytics, Toolkit },
  data() {
    return {
      currentPage: 'home',
      user: null,
      loading: true,
      mobileOpen: false,
      nav: [
        { id: 'home', label: '首页', icon: '⌂' },
        { id: 'blog', label: '博客', icon: '✦' },
        { id: 'news', label: '资讯', icon: '◫' },
        { id: 'analytics', label: 'App 观测', icon: '⌁' },
        { id: 'toolkit', label: '工具', icon: '◇' },
        { id: 'accounting', label: '记账', icon: '¥' },
        { id: 'download', label: '下载', icon: '↓' }
      ]
    }
  },
  mounted() { this.initializeAuth() },
  methods: {
    async initializeAuth() {
      try {
        const { data: { session } } = await supabase.auth.getSession()
        this.user = session?.user || null
        supabase.auth.onAuthStateChange((_event, session) => { this.user = session?.user || null })
      } catch (error) {
        console.warn('认证服务暂不可用', error)
      } finally { this.loading = false }
    },
    navigateTo(page) {
      if (page === 'accounting' && !this.user) { this.currentPage = 'auth' }
      else this.currentPage = page
      this.mobileOpen = false
      document.querySelector('.page-content')?.scrollTo(0, 0)
    },
    handleAuthSuccess(user) { this.user = user; this.currentPage = 'home' },
    async logout() {
      if (!confirm('确定要退出登录吗？')) return
      await supabase.auth.signOut()
      this.user = null
      this.currentPage = 'home'
    }
  }
}
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <button class="brand" @click="navigateTo('home')" aria-label="返回首页">
        <span class="brand-mark">Z</span>
        <span><b>ZHANG SPACE</b><small>张红星的数字花园</small></span>
      </button>
      <nav :class="{ open: mobileOpen }">
        <button v-for="item in nav" :key="item.id" :class="{ active: currentPage === item.id }" @click="navigateTo(item.id)">
          <span>{{ item.icon }}</span>{{ item.label }}
        </button>
      </nav>
      <div class="account-actions">
        <button v-if="user" class="avatar" :title="user.email" @click="logout">{{ user.email?.[0]?.toUpperCase() }}</button>
        <button v-else class="login-btn" @click="navigateTo('auth')">登录</button>
        <button class="menu-btn" @click="mobileOpen = !mobileOpen" aria-label="打开菜单">☰</button>
      </div>
    </header>

    <main class="page-content">
      <div v-if="loading" class="loading-screen"><span></span><p>正在抵达数字空间…</p></div>
      <Home v-else-if="currentPage === 'home'" @navigate="navigateTo" />
      <Blog v-else-if="currentPage === 'blog'" />
      <News v-else-if="currentPage === 'news'" />
      <Analytics v-else-if="currentPage === 'analytics'" />
      <Toolkit v-else-if="currentPage === 'toolkit'" />
      <Accounting v-else-if="currentPage === 'accounting'" />
      <Auth v-else-if="currentPage === 'auth'" @auth-success="handleAuthSuccess" />
      <Download v-else-if="currentPage === 'download'" />
    </main>
  </div>
</template>

<style>
:root { --ink:#16201d; --muted:#66736f; --cream:#f5f2ea; --paper:#fffdf8; --green:#174f42; --lime:#c8f560; --line:#dcded5; }
* { box-sizing:border-box; }
body { margin:0; background:var(--cream); color:var(--ink); font-family:Inter, "PingFang SC", "Microsoft YaHei", sans-serif; }
button,input,textarea { font:inherit; }
button { color:inherit; }
.app-shell { min-height:100vh; }
.topbar { height:74px; padding:0 4vw; display:flex; align-items:center; justify-content:space-between; position:fixed; inset:0 0 auto; z-index:100; background:rgba(245,242,234,.92); border-bottom:1px solid var(--line); backdrop-filter:blur(18px); }
.brand { display:flex; align-items:center; gap:10px; border:0; background:none; cursor:pointer; text-align:left; }
.brand-mark { width:38px;height:38px;display:grid;place-items:center;background:var(--green);color:var(--lime);border-radius:12px;font-family:Georgia;font-size:22px; }
.brand b { display:block;font-size:12px;letter-spacing:1.8px; }.brand small{display:block;color:var(--muted);font-size:11px;margin-top:2px}
.topbar nav { display:flex;gap:2px; }
.topbar nav button { border:0;background:none;padding:10px 12px;border-radius:9px;cursor:pointer;color:var(--muted);font-size:14px; }
.topbar nav button span { margin-right:5px }.topbar nav button:hover,.topbar nav button.active{background:#e5e9de;color:var(--green)}
.account-actions { display:flex;align-items:center;gap:8px }.login-btn{border:0;background:var(--green);color:white;padding:9px 18px;border-radius:999px;cursor:pointer}.avatar{border:0;width:36px;height:36px;border-radius:50%;background:var(--lime);cursor:pointer;font-weight:800}.menu-btn{display:none;border:0;background:none;font-size:22px}
.page-content { padding-top:74px;min-height:100vh; }
.loading-screen{height:calc(100vh - 74px);display:grid;place-content:center;text-align:center;color:var(--muted)}.loading-screen span{width:34px;height:34px;border:3px solid #d4d9cc;border-top-color:var(--green);border-radius:50%;animation:spin 1s linear infinite;margin:auto}@keyframes spin{to{transform:rotate(360deg)}}
.page-wrap{max-width:1180px;margin:auto;padding:48px 24px 80px}.eyebrow{font-size:12px;letter-spacing:2px;text-transform:uppercase;color:var(--green);font-weight:800}.page-title{font-family:Georgia,"Songti SC",serif;font-size:clamp(38px,5vw,68px);line-height:1.04;margin:10px 0 14px;letter-spacing:-2px}.page-lead{color:var(--muted);font-size:17px;max-width:650px;line-height:1.8}
.pill{border:1px solid var(--line);background:var(--paper);padding:8px 14px;border-radius:999px;cursor:pointer}.pill.active{background:var(--green);color:white;border-color:var(--green)}
@media(max-width:900px){.menu-btn{display:block}.topbar nav{display:none;position:absolute;top:74px;left:0;right:0;padding:12px;background:var(--paper);border-bottom:1px solid var(--line);grid-template-columns:repeat(2,1fr)}.topbar nav.open{display:grid}.topbar nav button{text-align:left}.brand small{display:none}.page-wrap{padding:32px 18px 60px}}
</style>
