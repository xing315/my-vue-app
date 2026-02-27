<script>
import { supabase } from './supabase.js'

export default {
  name: 'Auth',
  data() {
    return {
      isLogin: true,
      formData: {
        email: '',
        password: '',
        confirmPassword: ''
      },
      error: '',
      loading: false
    }
  },
  methods: {
    async handleSubmit() {
      this.error = ''
      this.loading = true
      
      try {
        if (!this.isLogin && this.formData.password !== this.formData.confirmPassword) {
          throw new Error('密码和确认密码不一致')
        }
        
        let result
        if (this.isLogin) {
          // 登录
          console.log('尝试登录:', this.formData.email)
          result = await supabase.auth.signInWithPassword({
            email: this.formData.email,
            password: this.formData.password
          })
        } else {
          // 注册
          console.log('尝试注册:', this.formData.email)
          result = await supabase.auth.signUp({
            email: this.formData.email,
            password: this.formData.password
          })
        }
        
        if (result.error) {
          console.error('认证失败:', result.error)
          throw result.error
        }
        
        // 登录成功后，保存用户信息到本地存储
        if (result.data.user) {
          console.log('认证成功:', result.data.user)
          localStorage.setItem('user', JSON.stringify(result.data.user))
          this.$emit('auth-success', result.data.user)
        }
      } catch (error) {
        console.error('认证错误:', error)
        this.error = error.message || '操作失败，请重试'
      } finally {
        this.loading = false
      }
    },
    toggleMode() {
      this.isLogin = !this.isLogin
      this.error = ''
      this.formData = {
        email: '',
        password: '',
        confirmPassword: ''
      }
    }
  }
}
</script>

<template>
  <div class="auth-container">
    <div class="auth-card">
      <h1>{{ isLogin ? '登录' : '注册' }}</h1>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <label>邮箱</label>
          <input 
            type="email" 
            v-model="formData.email" 
            required 
            placeholder="请输入邮箱"
          >
        </div>
        
        <div class="form-group">
          <label>密码</label>
          <input 
            type="password" 
            v-model="formData.password" 
            required 
            placeholder="请输入密码"
            :minlength="6"
          >
        </div>
        
        <div v-if="!isLogin" class="form-group">
          <label>确认密码</label>
          <input 
            type="password" 
            v-model="formData.confirmPassword" 
            required 
            placeholder="请再次输入密码"
            :minlength="6"
          >
        </div>
        
        <button 
          type="submit" 
          class="btn-primary" 
          :disabled="loading"
        >
          {{ loading ? '处理中...' : (isLogin ? '登录' : '注册') }}
        </button>
      </form>
      
      <div class="toggle-mode">
        {{ isLogin ? '还没有账号？' : '已有账号？' }}
        <button class="btn-link" @click="toggleMode">
          {{ isLogin ? '立即注册' : '去登录' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.auth-card {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 15px;
  padding: 40px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.auth-card h1 {
  color: #333;
  margin-bottom: 30px;
  font-size: 28px;
  font-weight: 700;
}

.error-message {
  background: #ff6b6b;
  color: white;
  padding: 10px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
}

.form-group {
  margin-bottom: 20px;
  text-align: left;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: #555;
  font-weight: 500;
}

.form-group input {
  width: 100%;
  padding: 12px 15px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s ease;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  width: 100%;
  margin-top: 10px;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.toggle-mode {
  margin-top: 20px;
  font-size: 14px;
  color: #666;
}

.btn-link {
  background: none;
  border: none;
  color: #667eea;
  font-weight: 600;
  cursor: pointer;
  padding: 0;
  font-size: 14px;
  text-decoration: underline;
  margin-left: 5px;
}

.btn-link:hover {
  color: #764ba2;
}
</style>
