<script>
import { supabase } from './supabase.js'

export default {
  data() {
    return {
      newTransaction: {
        date: new Date().toISOString().split('T')[0],
        person: '丈夫',
        amount: '',
        category: '餐饮',
        description: ''
      },
      transactions: [],
      currentUser: null,
      loading: false
    }
  },
  mounted() {
    this.getCurrentUser()
    this.loadTransactions()
  },
  computed: {
    totalAmount() {
      return this.transactions.reduce((total, transaction) => total + transaction.amount, 0)
    },
    husbandTotal() {
      return this.transactions
        .filter(transaction => transaction.person === '丈夫')
        .reduce((total, transaction) => total + transaction.amount, 0)
    },
    wifeTotal() {
      return this.transactions
        .filter(transaction => transaction.person === '妻子')
        .reduce((total, transaction) => total + transaction.amount, 0)
    },
    categoryTotals() {
      const totals = {}
      this.transactions.forEach(transaction => {
        if (!totals[transaction.category]) {
          totals[transaction.category] = 0
        }
        totals[transaction.category] += transaction.amount
      })
      return totals
    }
  },
  methods: {
    async getCurrentUser() {
      try {
        console.log('正在获取当前用户...')
        const { data: { user }, error: authError } = await supabase.auth.getUser()
        
        if (authError) {
          console.error('获取用户失败:', authError)
          this.currentUser = null
          return
        }
        
        this.currentUser = user
        console.log('当前用户:', user)
        if (user) {
          console.log('用户ID:', user.id)
          console.log('用户ID类型:', typeof user.id)
          console.log('用户ID格式是否为UUID:', this.isValidUUID(user.id))
          
          // 检查会话信息
          const { data: { session }, error: sessionError } = await supabase.auth.getSession()
          if (sessionError) {
            console.error('获取会话失败:', sessionError)
          } else {
            console.log('当前会话:', session)
            if (session) {
              console.log('会话令牌:', session.access_token.substring(0, 20) + '...')
            }
          }
        }
      } catch (error) {
        console.error('获取用户失败:', error)
        this.currentUser = null
      }
    },
    isValidUUID(str) {
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
      return uuidRegex.test(str)
    },
    async addTransaction() {
      if (this.newTransaction.amount && this.newTransaction.amount > 0) {
        try {
          this.loading = true
          // 确保获取最新的用户信息
          await this.getCurrentUser()
          
          if (!this.currentUser || !this.currentUser.id) {
            alert('用户未登录，请先登录')
            return
          }
          
          console.log('添加交易前的用户信息:', this.currentUser)
          console.log('用户ID:', this.currentUser.id)
          console.log('用户ID类型:', typeof this.currentUser.id)
          console.log('用户ID格式是否为UUID:', this.isValidUUID(this.currentUser.id))
          
          const transactionData = {
            date: this.newTransaction.date,
            person: this.newTransaction.person,
            amount: parseFloat(this.newTransaction.amount),
            category: this.newTransaction.category,
            description: this.newTransaction.description,
            user_id: this.currentUser.id
          }
          
          console.log('准备添加的交易数据:', transactionData)
          console.log('Supabase 配置:', {
            url: import.meta.env.VITE_SUPABASE_URL,
            anonKey: import.meta.env.VITE_SUPABASE_ANON_KEY ? '已配置' : '未配置'
          })
          
          const { data, error } = await supabase
            .from('transactions')
            .insert([transactionData])
            .select()
          
          console.log('添加交易结果:', { data, error })
          
          if (error) {
            console.error('添加交易失败:', error)
            console.error('错误详情:', {
              message: error.message,
              code: error.code,
              hint: error.hint,
              details: error.details
            })
            throw error
          }
          
          if (data && data.length > 0) {
            this.transactions.push(data[0])
            this.resetForm()
            alert('添加成功！')
          }
        } catch (error) {
          console.error('添加交易失败:', error)
          alert(`添加失败: ${error.message || '请检查网络连接和 Supabase 配置'}`)
        } finally {
          this.loading = false
        }
      }
    },
    async loadTransactions() {
      try {
        // 确保获取最新的用户信息
        await this.getCurrentUser()
        
        if (!this.currentUser || !this.currentUser.id) {
          console.log('用户未登录，无法加载交易数据')
          return
        }
        
        console.log('加载交易数据，用户ID:', this.currentUser.id)
        
        const { data, error } = await supabase
          .from('transactions')
          .select('*')
          .eq('user_id', this.currentUser.id)
          .order('date', { ascending: false })
        
        console.log('加载交易数据结果:', { data, error })
        
        if (error) {
          console.error('加载交易数据失败:', error)
          throw error
        }
        
        console.log('加载的数据:', data)
        this.transactions = data || []
      } catch (error) {
        console.error('加载交易数据失败:', error)
      }
    },
    async deleteTransaction(id) {
      try {
        // 确保获取最新的用户信息
        await this.getCurrentUser()
        
        if (!this.currentUser || !this.currentUser.id) {
          alert('用户未登录，请先登录')
          return
        }
        
        const { error } = await supabase
          .from('transactions')
          .delete()
          .eq('id', id)
          .eq('user_id', this.currentUser.id)
        
        if (error) {
          console.error('删除交易失败:', error)
          throw error
        }
        
        this.transactions = this.transactions.filter(transaction => transaction.id !== id)
        alert('删除成功！')
      } catch (error) {
        console.error('删除交易失败:', error)
        alert(`删除失败: ${error.message || '请检查网络连接和 Supabase 配置'}`)
      }
    },
    async clearAll() {
      if (!confirm('确定要清空所有数据吗？')) return
      
      try {
        // 确保获取最新的用户信息
        await this.getCurrentUser()
        
        if (!this.currentUser || !this.currentUser.id) {
          alert('用户未登录，请先登录')
          return
        }
        
        const { error } = await supabase
          .from('transactions')
          .delete()
          .eq('user_id', this.currentUser.id)
        
        if (error) {
          console.error('清空数据失败:', error)
          throw error
        }
        
        this.transactions = []
        alert('清空成功！')
      } catch (error) {
        console.error('清空数据失败:', error)
        alert(`清空失败: ${error.message || '请检查网络连接和 Supabase 配置'}`)
      }
    },
    resetForm() {
      this.newTransaction = {
        date: new Date().toISOString().split('T')[0],
        person: '丈夫',
        amount: '',
        category: '餐饮',
        description: ''
      }
    }
  }
}
</script>

<template>
  <div class="accounting-container">
    <h1>家庭记账</h1>
    
    <div class="form-section">
      <h2>添加支出</h2>
      <form @submit.prevent="addTransaction" class="transaction-form">
        <div class="form-row">
          <div class="form-group">
            <label for="date">日期</label>
            <input type="date" id="date" v-model="newTransaction.date" required>
          </div>
          <div class="form-group">
            <label for="person">支出人</label>
            <select id="person" v-model="newTransaction.person" required>
              <option value="丈夫">丈夫</option>
              <option value="妻子">妻子</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="amount">金额</label>
            <input type="number" id="amount" v-model="newTransaction.amount" step="0.01" min="0.01" required>
          </div>
          <div class="form-group">
            <label for="category">类别</label>
            <select id="category" v-model="newTransaction.category" required>
              <option value="餐饮">餐饮</option>
              <option value="购物">购物</option>
              <option value="交通">交通</option>
              <option value="娱乐">娱乐</option>
              <option value="医疗">医疗</option>
              <option value="教育">教育</option>
              <option value="其他">其他</option>
            </select>
          </div>
        </div>
        <div class="form-group full-width">
          <label for="description">描述</label>
          <input type="text" id="description" v-model="newTransaction.description">
        </div>
        <button type="submit" class="btn-add" :disabled="loading">
          {{ loading ? '添加中...' : '添加支出' }}
        </button>
      </form>
    </div>
    
    <div class="stats-section">
      <h2>统计信息</h2>
      <div class="stats-grid">
        <div class="stat-card">
          <h3>总支出</h3>
          <p class="stat-value">¥{{ totalAmount.toFixed(2) }}</p>
        </div>
        <div class="stat-card">
          <h3>丈夫支出</h3>
          <p class="stat-value">¥{{ husbandTotal.toFixed(2) }}</p>
        </div>
        <div class="stat-card">
          <h3>妻子支出</h3>
          <p class="stat-value">¥{{ wifeTotal.toFixed(2) }}</p>
        </div>
      </div>
      
      <div class="category-stats">
        <h3>类别支出</h3>
        <div class="category-list">
          <div v-for="(amount, category) in categoryTotals" :key="category" class="category-item">
            <span class="category-name">{{ category }}</span>
            <span class="category-amount">¥{{ amount.toFixed(2) }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <div class="transactions-section">
      <div class="section-header">
        <h2>支出记录</h2>
        <button class="btn-clear" @click="clearAll">清空记录</button>
      </div>
      <div class="transactions-list">
        <div v-if="transactions.length === 0" class="empty-state">
          <p>暂无支出记录</p>
        </div>
        <div v-for="transaction in transactions" :key="transaction.id" class="transaction-item">
          <div class="transaction-info">
            <div class="transaction-date">{{ transaction.date }}</div>
            <div class="transaction-person">{{ transaction.person }}</div>
            <div class="transaction-category">{{ transaction.category }}</div>
            <div class="transaction-description">{{ transaction.description || '无' }}</div>
          </div>
          <div class="transaction-amount">¥{{ transaction.amount.toFixed(2) }}</div>
          <button class="btn-delete" @click="deleteTransaction(transaction.id)">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.accounting-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
  font-family: 'Arial', sans-serif;
}

h1 {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 2.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

h2 {
  color: #555;
  margin-bottom: 20px;
  font-size: 1.5rem;
}

.form-section {
  background: white;
  border-radius: 10px;
  padding: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.transaction-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-row {
  display: flex;
  gap: 20px;
}

.form-group {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.form-group.full-width {
  flex: 1 1 100%;
}

label {
  font-weight: 500;
  color: #666;
  font-size: 14px;
}

input, select {
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 16px;
  transition: border-color 0.3s ease;
}

input:focus, select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
}

.btn-add {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  align-self: flex-start;
}

.btn-add:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.btn-add:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

.stats-section {
  background: white;
  border-radius: 10px;
  padding: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 30px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 20px;
  border-radius: 10px;
  text-align: center;
  transition: transform 0.3s ease;
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.stat-card h3 {
  color: #555;
  margin-bottom: 10px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stat-value {
  font-size: 24px;
  font-weight: bold;
  color: #333;
}

.category-stats {
  margin-top: 30px;
}

.category-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
}

.category-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  background: #f8f9fa;
  border-radius: 6px;
  transition: background 0.3s ease;
}

.category-item:hover {
  background: #e9ecef;
}

.category-name {
  font-weight: 500;
  color: #555;
}

.category-amount {
  font-weight: bold;
  color: #333;
}

.transactions-section {
  background: white;
  border-radius: 10px;
  padding: 30px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.btn-clear {
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-clear:hover {
  background: #ee5a52;
}

.transactions-list {
  max-height: 400px;
  overflow-y: auto;
  border-top: 1px solid #eee;
  padding-top: 20px;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #999;
  font-style: italic;
}

.transaction-item {
  display: flex;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #eee;
  transition: background 0.3s ease;
}

.transaction-item:hover {
  background: #f8f9fa;
}

.transaction-info {
  flex: 1;
  display: grid;
  grid-template-columns: 100px 80px 100px 1fr;
  gap: 15px;
}

.transaction-date {
  color: #666;
  font-size: 14px;
}

.transaction-person {
  font-weight: 500;
  color: #333;
}

.transaction-category {
  color: #666;
  font-size: 14px;
}

.transaction-description {
  color: #999;
  font-size: 14px;
}

.transaction-amount {
  font-weight: bold;
  color: #333;
  margin: 0 20px;
  min-width: 80px;
  text-align: right;
}

.btn-delete {
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-delete:hover {
  background: #ee5a52;
}

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .transaction-info {
    grid-template-columns: 1fr;
    gap: 5px;
  }
  
  .transaction-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
  
  .transaction-amount {
    margin: 0;
    text-align: left;
  }
  
  .btn-delete {
    align-self: flex-start;
  }
}
</style>
