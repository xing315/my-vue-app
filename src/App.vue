<script>
import Home from './Home.vue'
import Accounting from './Accounting.vue'

export default {
  components: {
    Home,
    Accounting
  },
  data() {
    return {
      currentPage: 'home'
    }
  },
  methods: {
    navigateTo(page) {
      this.currentPage = page
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
    </nav>
    
    <div class="page-content">
      <Home v-if="currentPage === 'home'" />
      <Accounting v-else-if="currentPage === 'accounting'" />
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

.page-content {
  width: 100%;
  height: 100%;
  padding-top: 60px;
  overflow-y: auto;
}
</style>
