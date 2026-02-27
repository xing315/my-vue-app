<script>
export default {
  name: 'FamilyAccounting',
  data() {
    return {
      transactions: [],
      newTransaction: {
        date: new Date().toISOString().split('T')[0],
        person: 'husband',
        amount: '',
        category: 'food',
        description: ''
      },
      categories: [
        { value: 'food', label: '餐饮' },
        { value: 'shopping', label: '购物' },
        { value: 'transport', label: '交通' },
        { value: 'entertainment', label: '娱乐' },
        { value: 'utilities', label: '水电' },
        { value: 'other', label: '其他' }
      ],
      dateRange: {
        start: '',
        end: ''
      },
      selectedPerson: 'all'
    }
  },
  mounted() {
    this.loadTransactions()
  },
  computed: {
    filteredTransactions() {
      let result = [...this.transactions]
      
      // 按日期范围过滤
      if (this.dateRange.start) {
        result = result.filter(t => t.date >= this.dateRange.start)
      }
      if (this.dateRange.end) {
        result = result.filter(t => t.date <= this.dateRange.end)
      }
      
      // 按人员过滤
      if (this.selectedPerson !== 'all') {
        result = result.filter(t => t.person === this.selectedPerson)
      }
      
      // 按日期降序排序
      return result.sort((a, b) => new Date(b.date) - new Date(a.date))
    },
    totalAmount() {
      return this.filteredTransactions.reduce((sum, t) => sum + parseFloat(t.amount), 0)
    },
    husbandTotal() {
      return this.transactions.filter(t => t.person === 'husband').reduce((sum, t) => sum + parseFloat(t.amount), 0)
    },
    wifeTotal() {
      return this.transactions.filter(t => t.person === 'wife').reduce((sum, t) => sum + parseFloat(t.amount), 0)
    },
    categoryStats() {
      const stats = {}
      this.transactions.forEach(t => {
        if (!stats[t.category]) {
          stats[t.category] = 0
        }
        stats[t.category] += parseFloat(t.amount)
      })
      return stats
    },
    dailyStats() {
      const stats = {}
      this.transactions.forEach(t => {
        if (!stats[t.date]) {
          stats[t.date] = 0
        }
        stats[t.date] += parseFloat(t.amount)
      })
      return stats
    }
  },
  methods: {
    addTransaction() {
      if (this.newTransaction.amount && this.newTransaction.amount > 0) {
        const transaction = {
          id: Date.now().toString(),
          ...this.newTransaction
        }
        this.transactions.push(transaction)
        this.saveTransactions()
        this.resetForm()
      }
    },
    deleteTransaction(id) {
      this.transactions = this.transactions.filter(t => t.id !== id)
      this.saveTransactions()
    },
    resetForm() {
      this.newTransaction = {
        date: new Date().toISOString().split('T')[0],
        person: 'husband',
        amount: '',
        category: 'food',
        description: ''
      }
    },
    saveTransactions() {
      localStorage.setItem('familyTransactions', JSON.stringify(this.transactions))
    },
    loadTransactions() {
      const saved = localStorage.getItem('familyTransactions')
      if (saved) {
        this.transactions = JSON.parse(saved)
      }
    },
    formatDate(dateStr) {
      const date = new Date(dateStr)
      return date.toLocaleDateString('zh-CN')
    },
    getCategoryLabel(value) {
      const category = this.categories.find(c => c.value === value)
      return category ? category.label : value
    },
    getPersonLabel(value) {
      return value === 'husband' ? '丈夫' : '妻子'
    },
    clearAll() {
      if (confirm('确定要清空所有数据吗？')) {
        this.transactions = []
        this.saveTransactions()
      }
    }
  }
}
</script>

<template>
  <div class="accounting-container">
    <div class="header">
      <h1>家庭记账</h1>
      <div class="summary-cards">
        <div class="card">
          <h3>总支出</h3>
          <p class="amount">¥{{ totalAmount.toFixed(2) }}</p>
        </div>
        <div class="card">
          <h3>丈夫支出</h3>
          <p class="amount">¥{{ husbandTotal.toFixed(2) }}</p>
        </div>
        <div class="card">
          <h3>妻子支出</h3>
          <p class="amount">¥{{ wifeTotal.toFixed(2) }}</p>
        </div>
      </div>
    </div>
    
    <div class="main-content">
      <div class="left-panel">
        <div class="form-card">
          <h2>添加支出</h2>
          <form @submit.prevent="addTransaction">
            <div class="form-row">
              <div class="form-group">
                <label>日期</label>
                <input type="date" v-model="newTransaction.date" required>
              </div>
              <div class="form-group">
                <label>人员</label>
                <select v-model="newTransaction.person" required>
                  <option value="husband">丈夫</option>
                  <option value="wife">妻子</option>
                </select>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>金额</label>
                <input type="number" v-model="newTransaction.amount" step="0.01" min="0.01" required>
              </div>
              <div class="form-group">
                <label>分类</label>
                <select v-model="newTransaction.category" required>
                  <option v-for="category in categories" :key="category.value" :value="category.value">
                    {{ category.label }}
                  </option>
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>描述</label>
              <input type="text" v-model="newTransaction.description" placeholder="可选">
            </div>
            <button type="submit" class="btn-primary">添加</button>
          </form>
        </div>
        
        <div class="filter-card">
          <h2>筛选</h2>
          <div class="form-row">
            <div class="form-group">
              <label>开始日期</label>
              <input type="date" v-model="dateRange.start">
            </div>
            <div class="form-group">
              <label>结束日期</label>
              <input type="date" v-model="dateRange.end">
            </div>
          </div>
          <div class="form-group">
            <label>人员</label>
            <select v-model="selectedPerson">
              <option value="all">全部</option>
              <option value="husband">丈夫</option>
              <option value="wife">妻子</option>
            </select>
          </div>
        </div>
      </div>
      
      <div class="right-panel">
        <div class="transactions-card">
          <div class="card-header">
            <h2>支出记录</h2>
            <button class="btn-danger" @click="clearAll">清空所有</button>
          </div>
          <div class="transaction-list">
            <div v-if="filteredTransactions.length === 0" class="empty-state">
              暂无记录
            </div>
            <div v-for="transaction in filteredTransactions" :key="transaction.id" class="transaction-item">
              <div class="transaction-info">
                <div class="transaction-date">{{ formatDate(transaction.date) }}</div>
                <div class="transaction-person">{{ getPersonLabel(transaction.person) }}</div>
                <div class="transaction-category">{{ getCategoryLabel(transaction.category) }}</div>
                <div class="transaction-description">{{ transaction.description || '无' }}</div>
              </div>
              <div class="transaction-amount">¥{{ parseFloat(transaction.amount).toFixed(2) }}</div>
              <button class="btn-delete" @click="deleteTransaction(transaction.id)">×</button>
            </div>
          </div>
        </div>
        
        <div class="stats-card">
          <h2>统计分析</h2>
          <div class="stats-grid">
            <div class="stat-item">
              <h3>分类统计</h3>
              <div v-for="(amount, category) in categoryStats" :key="category" class="stat-row">
                <span>{{ getCategoryLabel(category) }}</span>
                <span>¥{{ amount.toFixed(2) }}</span>
              </div>
            </div>
            <div class="stat-item">
              <h3>每日统计</h3>
              <div v-for="(amount, date) in dailyStats" :key="date" class="stat-row">
                <span>{{ formatDate(date) }}</span>
                <span>¥{{ amount.toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.accounting-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  overflow-y: auto;
  font-family: 'Inter', sans-serif;
}

.header {
  text-align: center;
  margin-bottom: 30px;
}

.header h1 {
  font-size: 48px;
  color: white;
  margin-bottom: 20px;
  text-shadow: 0 2px 10px rgba(0,0,0,0.3);
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.card {
  background: rgba(255,255,255,0.95);
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  backdrop-filter: blur(10px);
  text-align: center;
  transition: transform 0.3s ease;
}

.card:hover {
  transform: translateY(-5px);
}

.card h3 {
  color: #333;
  margin-bottom: 10px;
  font-size: 18px;
}

.card .amount {
  font-size: 28px;
  font-weight: bold;
  color: #667eea;
  margin: 0;
}

.main-content {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 30px;
  max-width: 1200px;
  margin: 0 auto;
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-card, .filter-card, .transactions-card, .stats-card {
  background: rgba(255,255,255,0.95);
  border-radius: 15px;
  padding: 25px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.1);
  backdrop-filter: blur(10px);
}

.form-card h2, .filter-card h2, .transactions-card h2, .stats-card h2 {
  color: #333;
  margin-bottom: 20px;
  font-size: 24px;
  border-bottom: 2px solid #667eea;
  padding-bottom: 10px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 15px;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  color: #555;
  font-weight: 500;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s ease;
}

.form-group input:focus,
.form-group select:focus {
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

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-danger {
  background: #ff6b6b;
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-danger:hover {
  background: #ee5a52;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.transaction-list {
  max-height: 400px;
  overflow-y: auto;
}

.transaction-item {
  display: flex;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #f0f0f0;
  transition: background 0.2s ease;
}

.transaction-item:hover {
  background: #f8f9fa;
}

.transaction-info {
  flex: 1;
  display: grid;
  grid-template-columns: 120px 80px 100px 1fr;
  gap: 10px;
}

.transaction-date {
  font-weight: 500;
  color: #666;
}

.transaction-person {
  color: #667eea;
  font-weight: 600;
}

.transaction-category {
  color: #764ba2;
  font-weight: 500;
}

.transaction-description {
  color: #888;
  font-size: 14px;
}

.transaction-amount {
  font-weight: bold;
  color: #ff6b6b;
  margin: 0 20px;
  min-width: 80px;
  text-align: right;
}

.btn-delete {
  background: #ff6b6b;
  color: white;
  border: none;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s ease;
}

.btn-delete:hover {
  background: #ee5a52;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #999;
  font-style: italic;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.stat-item {
  background: #f8f9fa;
  border-radius: 10px;
  padding: 15px;
}

.stat-item h3 {
  color: #333;
  margin-bottom: 15px;
  font-size: 16px;
  border-bottom: 1px solid #e0e0e0;
  padding-bottom: 8px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f0f0;
}

.stat-row:last-child {
  border-bottom: none;
}

@media (max-width: 768px) {
  .main-content {
    grid-template-columns: 1fr;
  }
  
  .form-row {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .transaction-info {
    grid-template-columns: 1fr;
    gap: 5px;
  }
}
</style>
