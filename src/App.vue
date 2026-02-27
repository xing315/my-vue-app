<script>
import Home from './Home.vue'
import Accounting from './Accounting.vue'
import Auth from './Auth.vue'
import { supabase } from './supabase.js'

export default {
  components: {
    Home,
    Accounting,
    Auth
  },
  data() {
    return {
      currentPage: 'home',
      user: null,
      loading: true
    }
  },
  mounted() {
    this.initializeAuth()
  },
  methods: {
    async initializeAuth() {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        
        if (error) {
          console.error('获取会话失败:', error)
          this.loading = false
          return
        }
        
        if (session?.user) {
          this.user = session.user
          console.log('会话恢复成功:', this.user)
          localStorage.setItem('user', JSON.stringify(this.user))
        } else {
          console.log('没有有效的会话，用户需要登录')
          localStorage.removeItem('user')
        }
        
        supabase.auth.onAuthStateChange((event, session) => {
          console.log('认证状态变化:', event, session)
          
          if (event === 'SIGNED_IN' && session?.user) {
            this.user = session.user
            localStorage.setItem('user', JSON.stringify(this.user))
            console.log('用户登录:', this.user)
          } else if (event === 'SIGNED_OUT') {
            this.user = null
            localStorage.removeItem('user')
            console.log('用户退出')
          } else if (event === 'TOKEN_REFRESHED' && session?.user) {
            this.user = session.user
            localStorage.setItem('user', JSON.stringify(this.user))
            console.log('令牌已刷新:', this.user)
          }
        })
      } catch (error) {
        console.error('初始化认证失败:', error)
      } finally {
        this.loading = false
      }
    },
    navigateTo(page) {
      if (page === 'accounting' && !this.user) {
        alert('请先登录')
        return
      }
      this.currentPage = page
    },
    handleAuthSuccess(user) {
      this.user = user
      console.log('认证成功的用户:', user)
      console.log('用户ID:', user.id)
      this.currentPage = 'home'
    },
    async logout() {
      if (!confirm('确定要退出登录吗？')) {
        return
      }
      
      try {
        const { error } = await supabase.auth.signOut()
        
        if (error) {
          console.error('退出登录失败:', error)
          alert('退出登录失败，请重试')
          return
        }
        
        this.user = null
        this.currentPage = 'home'
        localStorage.removeItem('user')
        console.log('用户已成功退出')
        
        alert('已退出登录')
      } catch (error) {
        console.error('退出登录异常:', error)
        alert('退出登录失败，请重试')
      }
    }
  }
}
</script>

<template>
  <div class="app-container">
    <nav class="navbar">
      <div class="nav-item" :class="{ active: currentPage === 'home' }" @click="navigateTo('home')">
        个人主页
      </div>
      <div class="nav-item" :class="{ active: currentPage === 'accounting' }" @click="navigateTo('accounting')">
        家庭记账
      </div>
      <div v-if="user" class="nav-user">
        <div class="user-info">
          <span class="user-email">{{ user.email }}</span>
          <span class="user-status">已登录</span>
        </div>
        <button class="btn-logout" @click="logout">
          <span class="logout-icon">🚪</span>
          退出
        </button>
      </div>
      <div v-else class="nav-item" @click="currentPage = 'auth'">
        登录/注册
      </div>
    </nav>
    
    <div class="page-content">
      <div v-if="loading" class="loading-container">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>
      <Home v-else-if="currentPage === 'home'" />
      <Accounting v-else-if="currentPage === 'accounting'" />
      <Auth v-else-if="currentPage === 'auth'" @auth-success="handleAuthSuccess" />
    </div>
  </div>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.app-container {
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

.navbar {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: center;
  z-index: 1000;
  padding: 0 20px;
}

.nav-item {
  padding: 15px 30px;
  font-size: 18px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  color: #333;
  border-bottom: 3px solid transparent;
}

.nav-item:hover {
  color: #667eea;
}

.nav-item.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.nav-user {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.user-email {
  color: #333;
  font-weight: 500;
  font-size: 14px;
}

.user-status {
  color: #4CAF50;
  font-size: 12px;
  font-weight: 600;
}

.btn-logout {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(255, 107, 107, 0.3);
}

.btn-logout:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(255, 107, 107, 0.4);
}

.btn-logout:active {
  transform: translateY(0);
}

.logout-icon {
  font-size: 16px;
}

.page-content {
  width: 100%;
  height: 100%;
  padding-top: 60px;
  overflow-y: auto;
}

.loading-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
