<script>
import { supabase } from './supabase.js'

const today = () => new Date().toISOString().slice(0, 10)
const money = value => Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

export default {
  name: 'Members',
  props: { user: { type: Object, required: true } },
  data() {
    return {
      members: [], transactions: [], products: [], transactionItems: [], loading: true, submitting: false, error: '', search: '',
      maxDate: today(),
      showCreate: false, showCatalog: false, selected: null, action: '', reversalTarget: null, cart: {},
      createForm: { name: '', phone: '', notes: '', openingAmount: '', businessDate: today() },
      actionForm: { amount: '', businessDate: today(), note: '' },
      editForm: { name: '', notes: '' }, reversalReason: ''
    }
  },
  computed: {
    filteredMembers() {
      const q = this.search.trim().toLowerCase()
      const rows = q ? this.members.filter(m => m.name.toLowerCase().includes(q) || m.phone.includes(q)) : this.members
      return [...rows].sort((a, b) => (b.last_consumed_on || b.created_at).localeCompare(a.last_consumed_on || a.created_at))
    },
    memberTransactions() { return this.selected ? this.transactions.filter(t => t.member_id === this.selected.id) : [] },
    itemsByTransaction() {
      return this.transactionItems.reduce((map, item) => { (map[item.transaction_id] ||= []).push(item); return map }, {})
    },
    cartTotal() { return this.products.reduce((sum, p) => sum + Number(p.price) * Number(this.cart[p.id] || 0), 0) },
    cartCount() { return Object.values(this.cart).reduce((sum, value) => sum + Number(value || 0), 0) },
    favoriteProduct() {
      if (!this.selected) return null
      const txIds = new Set(this.memberTransactions.filter(t => t.transaction_type === 'consume' && !this.reversedIds.has(t.id)).map(t => t.id))
      const totals = {}
      this.transactionItems.filter(item => txIds.has(item.transaction_id)).forEach(item => { totals[item.product_name + '|' + item.variant] = (totals[item.product_name + '|' + item.variant] || 0) + item.quantity })
      const winner = Object.entries(totals).sort((a, b) => b[1] - a[1])[0]
      return winner ? { name: winner[0].replace('|', ' · '), count: winner[1] } : null
    },
    lastOrder() {
      if (!this.selected) return null
      return this.memberTransactions.find(t => t.transaction_type === 'consume' && !this.reversedIds.has(t.id) && this.itemsByTransaction[t.id]?.length)
    },
    lastOrderItems() { return this.lastOrder ? this.itemsByTransaction[this.lastOrder.id] || [] : [] },
    pairingSuggestion() {
      const selectedProducts = this.products.filter(p => Number(this.cart[p.id] || 0) > 0)
      const hasDuck = selectedProducts.some(p => p.category === '烤鸭' || p.category === '套餐')
      const hasSide = selectedProducts.some(p => p.sku === 'pancake')
      return hasDuck && !hasSide ? this.products.find(p => p.sku === 'pancake' && p.active) : null
    },
    topProduct() {
      const valid = new Set(this.transactions.filter(t => t.transaction_type === 'consume' && !this.reversedIds.has(t.id)).map(t => t.id))
      const totals = {}
      this.transactionItems.filter(item => valid.has(item.transaction_id)).forEach(item => { totals[item.product_name + '|' + item.variant] = (totals[item.product_name + '|' + item.variant] || 0) + item.quantity })
      const winner = Object.entries(totals).sort((a, b) => b[1] - a[1])[0]
      return winner ? { name: winner[0].replace('|', ' · '), count: winner[1] } : null
    },
    reversedIds() { return new Set(this.transactions.filter(t => t.original_transaction_id).map(t => t.original_transaction_id)) },
    stats() {
      const date = today()
      return {
        members: this.members.length,
        balance: this.members.reduce((sum, m) => sum + Number(m.balance), 0),
        spent: this.members.reduce((sum, m) => sum + Number(m.total_spent), 0),
        todaySpent: this.transactions.filter(t => t.business_date === date && t.transaction_type === 'consume' && !this.reversedIds.has(t.id)).reduce((sum, t) => sum + Number(t.amount), 0),
        todayNew: this.members.filter(m => m.created_at.slice(0, 10) === date).length
      }
    }
  },
  mounted() { this.loadData() },
  methods: {
    money,
    async loadData() {
      this.loading = true; this.error = ''
      try {
        const seeded = await supabase.rpc('ensure_default_membership_products')
        if (seeded.error) throw seeded.error
        const [memberResult, txResult, productResult, itemResult] = await Promise.all([
          supabase.from('members').select('*').order('created_at', { ascending: false }),
          supabase.from('member_transactions').select('*').order('created_at', { ascending: false }).limit(1000),
          supabase.from('membership_products').select('*').order('sort_order'),
          supabase.from('member_transaction_items').select('*').order('created_at', { ascending: false }).limit(3000)
        ])
        if (memberResult.error) throw memberResult.error
        if (txResult.error) throw txResult.error
        if (productResult.error) throw productResult.error
        if (itemResult.error) throw itemResult.error
        this.members = memberResult.data || []; this.transactions = txResult.data || []
        this.products = productResult.data || []; this.transactionItems = itemResult.data || []
        if (this.selected) this.selected = this.members.find(m => m.id === this.selected.id) || null
      } catch (e) { this.error = this.readError(e) }
      finally { this.loading = false }
    },
    readError(e) {
      const message = e?.message || '操作失败，请稍后重试'
      if (message.includes('relation') || message.includes('schema cache') || message.includes('create_member') || message.includes('ensure_default')) return '会员数据库尚未升级，请先执行最新的会员系统迁移文件。'
      if (message.includes('duplicate') || message.includes('已是会员')) return '该手机号已经是会员。'
      return message
    },
    openMember(member) {
      this.selected = member; this.action = ''; this.reversalTarget = null
      this.editForm = { name: member.name, notes: member.notes || '' }
    },
    closeDrawer() { this.selected = null; this.action = ''; this.reversalTarget = null },
    startAction(type) { this.action = type; this.reversalTarget = null; this.error = ''; this.cart = {}; this.actionForm = { amount: '', businessDate: today(), note: '' } },
    changeQuantity(productId, delta) {
      const next = Math.max(0, Math.min(99, Number(this.cart[productId] || 0) + delta))
      this.cart = { ...this.cart, [productId]: next }
    },
    repeatLastOrder() {
      if (!this.lastOrderItems.length) return
      this.startAction('consume')
      const next = {}
      this.lastOrderItems.forEach(item => { if (item.product_id && this.products.some(p => p.id === item.product_id && p.active)) next[item.product_id] = item.quantity })
      this.cart = next
      this.actionForm.note = '熟客照旧 · 复购上次订单'
    },
    memberStatus(member) {
      if (!member.last_consumed_on) return { label: '新会员', type: 'new' }
      const days = Math.floor((new Date(`${today()}T00:00:00`) - new Date(`${member.last_consumed_on}T00:00:00`)) / 86400000)
      if (days >= 45) return { label: `${days}天未到店`, type: 'sleep' }
      if (days <= 7) return { label: '近期活跃', type: 'active' }
      return { label: `${days}天前到店`, type: 'normal' }
    },
    async createMember() {
      if (!/^1[3-9]\d{9}$/.test(this.createForm.phone)) { this.error = '请输入正确的11位手机号。'; return }
      if (!this.createForm.name.trim()) { this.error = '请输入会员姓名。'; return }
      await this.run(async () => {
        const { error } = await supabase.rpc('create_member', {
          p_name: this.createForm.name, p_phone: this.createForm.phone, p_notes: this.createForm.notes,
          p_opening_amount: Number(this.createForm.openingAmount || 0), p_business_date: this.createForm.businessDate
        })
        if (error) throw error
        this.showCreate = false
        this.createForm = { name: '', phone: '', notes: '', openingAmount: '', businessDate: today() }
        await this.loadData()
      })
    },
    async submitAction() {
      if (this.action === 'consume' && this.cartCount > 0) return this.submitOrder()
      const amount = Number(this.actionForm.amount)
      if (!amount || amount <= 0) { this.error = '金额必须大于0。'; return }
      if (this.action === 'consume' && amount > Number(this.selected.balance)) { this.error = '会员余额不足。'; return }
      await this.run(async () => {
        const { error } = await supabase.rpc('apply_member_transaction', {
          p_member_id: this.selected.id, p_type: this.action, p_amount: amount,
          p_business_date: this.actionForm.businessDate, p_note: this.actionForm.note
        })
        if (error) throw error
        this.action = ''; await this.loadData()
      })
    },
    async submitOrder() {
      if (!this.cartCount) { this.error = '请至少选择一件菜品。'; return }
      if (this.cartTotal > Number(this.selected.balance)) { this.error = '会员余额不足。'; return }
      await this.run(async () => {
        const items = Object.entries(this.cart).filter(([, quantity]) => quantity > 0).map(([product_id, quantity]) => ({ product_id, quantity }))
        const { error } = await supabase.rpc('apply_member_order', { p_member_id: this.selected.id, p_items: items, p_business_date: this.actionForm.businessDate, p_note: this.actionForm.note })
        if (error) throw error
        this.action = ''; this.cart = {}; await this.loadData()
      })
    },
    async saveCatalog() {
      await this.run(async () => {
        for (const product of this.products) {
          const price = Number(product.price)
          if (price < 0) throw new Error('商品价格不能小于0。')
          const { error } = await supabase.from('membership_products').update({ price, active: product.active, updated_at: new Date().toISOString() }).eq('id', product.id)
          if (error) throw error
        }
        this.showCatalog = false; await this.loadData()
      })
    },
    async saveProfile() {
      if (!this.editForm.name.trim()) { this.error = '姓名不能为空。'; return }
      await this.run(async () => {
        const { error } = await supabase.from('members').update({ name: this.editForm.name.trim(), notes: this.editForm.notes.trim(), updated_at: new Date().toISOString() }).eq('id', this.selected.id)
        if (error) throw error
        await this.loadData()
      })
    },
    requestReversal(tx) { this.reversalTarget = tx; this.reversalReason = ''; this.action = ''; this.error = '' },
    async reverseTransaction() {
      if (this.reversalReason.trim().length < 2) { this.error = '请填写至少2个字的冲正原因。'; return }
      await this.run(async () => {
        const { error } = await supabase.rpc('reverse_member_transaction', { p_transaction_id: this.reversalTarget.id, p_reason: this.reversalReason })
        if (error) throw error
        this.reversalTarget = null; await this.loadData()
      })
    },
    async run(task) {
      if (this.submitting) return
      this.submitting = true; this.error = ''
      try { await task() } catch (e) { this.error = this.readError(e) }
      finally { this.submitting = false }
    },
    typeLabel(type) { return ({ recharge: '充值', consume: '消费', reversal: '冲正' })[type] || type },
    formatDate(date) { return date ? new Intl.DateTimeFormat('zh-CN').format(new Date(`${date}T00:00:00`)) : '暂无' }
  }
}
</script>

<template>
  <div class="member-page">
    <section class="member-hero">
      <img src="/images/members/roast-duck-menu.png" alt="金黄酥香的果木烤鸭">
      <div class="hero-copy"><p class="eyebrow">ROAST DUCK · MEMBER CRM</p><h1>会员管理</h1><p>记住熟客爱吃什么，也记住每一次到店。</p></div>
      <div class="hero-actions"><button class="catalog-btn" @click="showCatalog = true">菜品设置</button><button class="primary-btn" @click="showCreate = true; error = ''"><span>＋</span> 新增会员</button></div>
    </section>

    <div v-if="error" class="notice" role="alert"><span>!</span>{{ error }}<button @click="error = ''">×</button></div>

    <section class="stats-grid">
      <article><span>会员总数</span><strong>{{ stats.members }}</strong><small>人</small></article>
      <article><span>储值余额</span><strong>¥{{ money(stats.balance) }}</strong><small>当前沉淀</small></article>
      <article><span>累计消费</span><strong>¥{{ money(stats.spent) }}</strong><small>历史总计</small></article>
      <article><span>今日消费</span><strong>¥{{ money(stats.todaySpent) }}</strong><small>实时统计</small></article>
      <article><span>今日新增</span><strong>{{ stats.todayNew }}</strong><small>位会员</small></article>
    </section>

    <section class="insight-strip">
      <div><span class="insight-icon">♨</span><p><small>当前热销</small><b>{{ topProduct ? topProduct.name : '等待首笔菜品订单' }}</b></p><strong v-if="topProduct">{{ topProduct.count }} 份</strong></div>
      <p>系统会根据真实订单自动识别会员偏好和门店热销菜品，帮助店员更懂熟客。</p>
    </section>

    <section class="members-card">
      <div class="table-head"><div><h2>会员档案</h2><p>共 {{ filteredMembers.length }} 位会员</p></div><label class="search"><span>⌕</span><input v-model="search" placeholder="搜索姓名、手机号或后四位" aria-label="搜索会员"></label></div>
      <div v-if="loading" class="state">正在整理会员档案…</div>
      <div v-else-if="!filteredMembers.length" class="state empty"><b>◎</b><h3>{{ search ? '没有找到匹配会员' : '还没有会员档案' }}</h3><p>{{ search ? '换个姓名或手机号试试' : '新增第一位会员，开始记录每次到店' }}</p></div>
      <div v-else class="table-scroll"><table><thead><tr><th>会员</th><th>当前余额</th><th>累计消费</th><th>消费次数</th><th>最近消费</th><th></th></tr></thead>
        <tbody><tr v-for="member in filteredMembers" :key="member.id" @click="openMember(member)" tabindex="0" @keydown.enter="openMember(member)">
          <td><div class="member-cell"><span>{{ member.name.slice(0, 1) }}</span><div><b>{{ member.name }} <em :class="['member-status', memberStatus(member).type]">{{ memberStatus(member).label }}</em></b><small>{{ member.phone }}</small></div></div></td>
          <td class="balance">¥{{ money(member.balance) }}</td><td>¥{{ money(member.total_spent) }}</td><td>{{ member.visit_count }} 次</td><td>{{ formatDate(member.last_consumed_on) }}</td><td class="arrow">›</td>
        </tr></tbody></table></div>
    </section>

    <div v-if="showCreate" class="modal-layer" @click.self="showCreate = false"><section class="modal" role="dialog" aria-modal="true"><header><div><small>NEW MEMBER</small><h2>新增会员</h2></div><button @click="showCreate = false">×</button></header>
      <form @submit.prevent="createMember"><div class="form-grid"><label>会员姓名<input v-model="createForm.name" maxlength="50" placeholder="例如：王女士" required></label><label>手机号码<input v-model="createForm.phone" inputmode="numeric" maxlength="11" placeholder="11位手机号" required></label><label>首次充值（可选）<div class="money-input"><span>¥</span><input v-model="createForm.openingAmount" type="number" min="0" step="0.01" placeholder="0.00"></div></label><label>业务日期<input v-model="createForm.businessDate" type="date" :max="maxDate" required></label></div><label>会员备注<textarea v-model="createForm.notes" maxlength="500" placeholder="口味偏好、送餐地址或其他提醒"></textarea></label><footer><button type="button" class="ghost-btn" @click="showCreate = false">取消</button><button class="primary-btn" :disabled="submitting">{{ submitting ? '正在保存…' : '确认建档' }}</button></footer></form>
    </section></div>

    <div v-if="showCatalog" class="modal-layer" @click.self="showCatalog = false"><section class="modal catalog-modal" role="dialog" aria-modal="true"><header><div><small>MENU SETTINGS</small><h2>菜品与售价</h2></div><button @click="showCatalog = false">×</button></header>
      <form @submit.prevent="saveCatalog"><p class="catalog-lead">首版已准备烤鸭常用规格，价格可以按门店实际情况修改，下架后点单时不再显示。</p><div class="catalog-list"><article v-for="product in products" :key="product.id"><img :src="product.image_url" :alt="product.name"><div><b>{{ product.name }}</b><span>{{ product.variant }} · {{ product.category }}</span></div><label class="catalog-price">售价<div class="money-input"><span>¥</span><input v-model.number="product.price" type="number" min="0" step="0.01" required></div></label><label class="switch"><input v-model="product.active" type="checkbox"><i></i><span>{{ product.active ? '上架' : '下架' }}</span></label></article></div><footer><button type="button" class="ghost-btn" @click="showCatalog = false">取消</button><button class="primary-btn" :disabled="submitting">{{ submitting ? '正在保存…' : '保存菜品' }}</button></footer></form>
    </section></div>

    <div v-if="selected" class="drawer-layer" @click.self="closeDrawer"><aside class="drawer"><header class="drawer-head"><button class="close" @click="closeDrawer">×</button><div class="avatar-large">{{ selected.name.slice(0, 1) }}</div><div><h2>{{ selected.name }}</h2><p>{{ selected.phone }} · 加入于 {{ formatDate(selected.created_at.slice(0,10)) }}</p></div></header>
      <div class="drawer-balance"><span>当前储值余额</span><strong>¥{{ money(selected.balance) }}</strong><div><button @click="startAction('consume')">消费扣款</button><button @click="startAction('recharge')">会员充值</button></div></div>
      <div class="mini-stats"><div><span>累计充值</span><b>¥{{ money(selected.total_recharged) }}</b></div><div><span>累计消费</span><b>¥{{ money(selected.total_spent) }}</b></div><div><span>到店次数</span><b>{{ selected.visit_count }} 次</b></div></div>
      <div class="preference-card"><span>熟客偏好</span><b>{{ favoriteProduct ? favoriteProduct.name : '消费后自动识别' }}</b><small v-if="favoriteProduct">累计购买 {{ favoriteProduct.count }} 份</small></div>
      <div class="memory-card" :class="memberStatus(selected).type"><div class="memory-icon">✦</div><div><span>熟客记忆</span><b v-if="lastOrder">上次点了 {{ lastOrderItems.map(i => `${i.product_name}${i.variant}×${i.quantity}`).join('、') }}</b><b v-else>第一次到店，给 TA 留下好印象</b><small v-if="lastOrder">{{ formatDate(lastOrder.business_date) }} · {{ memberStatus(selected).label }}</small><small v-else>完成首笔菜品订单后，这里会自动记住常点内容</small></div><button v-if="lastOrder" @click="repeatLastOrder">一键照旧</button></div>

      <form v-if="action === 'consume'" class="action-panel order-panel" @submit.prevent="submitOrder"><div class="panel-title"><div><b>菜品点单</b><small>选择规格与数量，自动计算扣款</small></div><button type="button" @click="action = ''">×</button></div><div class="product-picker"><article v-for="product in products.filter(p => p.active)" :key="product.id" :class="{ picked: cart[product.id] }"><img :src="product.image_url" :alt="product.name"><div class="product-info"><b>{{ product.name }}</b><span>{{ product.variant }}</span><strong>¥{{ money(product.price) }}</strong></div><div class="stepper"><button type="button" aria-label="减少数量" @click="changeQuantity(product.id, -1)">−</button><em>{{ cart[product.id] || 0 }}</em><button type="button" aria-label="增加数量" @click="changeQuantity(product.id, 1)">＋</button></div></article></div><button v-if="pairingSuggestion" type="button" class="pairing-tip" @click="changeQuantity(pairingSuggestion.id, 1)"><span>搭配建议</span>加一套荷叶饼，让这份烤鸭更完整 <b>＋¥{{ money(pairingSuggestion.price) }}</b></button><div class="form-grid order-fields"><label>业务日期<input v-model="actionForm.businessDate" type="date" :max="maxDate" required></label><label>订单备注<input v-model="actionForm.note" maxlength="500" placeholder="桌号、口味或打包提醒"></label></div><div class="order-total"><span>共 {{ cartCount }} 件</span><b>合计 ¥{{ money(cartTotal) }}</b></div><button class="primary-btn full" :disabled="submitting || !cartCount">{{ submitting ? '正在扣款…' : '确认订单并扣款' }}</button></form>
      <form v-if="action === 'recharge'" class="action-panel" @submit.prevent="submitAction"><div class="panel-title"><b>会员充值</b><button type="button" @click="action = ''">×</button></div><div class="form-grid"><label>金额<div class="money-input"><span>¥</span><input v-model="actionForm.amount" type="number" min="0.01" step="0.01" required autofocus></div></label><label>业务日期<input v-model="actionForm.businessDate" type="date" :max="maxDate" required></label></div><label>备注<input v-model="actionForm.note" maxlength="500" placeholder="例如：充值赠送活动"></label><button class="primary-btn full" :disabled="submitting">{{ submitting ? '处理中…' : '确认充值' }}</button></form>
      <form v-if="reversalTarget" class="action-panel danger-panel" @submit.prevent="reverseTransaction"><div class="panel-title"><b>冲正 {{ typeLabel(reversalTarget.transaction_type) }} ¥{{ money(reversalTarget.amount) }}</b><button type="button" @click="reversalTarget = null">×</button></div><p>冲正会生成一笔反向流水，原记录将永久保留。</p><label>冲正原因<input v-model="reversalReason" maxlength="500" placeholder="例如：店员金额录入错误" required></label><button class="danger-btn full" :disabled="submitting">{{ submitting ? '处理中…' : '确认冲正' }}</button></form>

      <section class="drawer-section"><h3>会员资料</h3><div class="form-grid"><label>会员姓名<input v-model="editForm.name" maxlength="50"></label><label>手机号码<input :value="selected.phone" disabled></label></div><label>备注<textarea v-model="editForm.notes" maxlength="500" placeholder="暂无备注"></textarea></label><button class="text-btn" :disabled="submitting" @click="saveProfile">保存资料</button></section>
      <section class="drawer-section"><div class="section-title"><h3>资金流水</h3><span>{{ memberTransactions.length }} 笔</span></div><div v-if="!memberTransactions.length" class="small-empty">暂无充值或消费记录</div><div v-else class="timeline"><article v-for="tx in memberTransactions" :key="tx.id" :class="[tx.transaction_type, { reversed: reversedIds.has(tx.id) }]">
        <i></i><div class="tx-main"><div><b>{{ typeLabel(tx.transaction_type) }}</b><em v-if="reversedIds.has(tx.id)">已冲正</em><small>{{ formatDate(tx.business_date) }} · {{ tx.note || '无备注' }}</small></div><strong :class="tx.balance_delta > 0 ? 'positive' : 'negative'">{{ tx.balance_delta > 0 ? '+' : '-' }}¥{{ money(Math.abs(tx.balance_delta)) }}</strong></div><div v-if="itemsByTransaction[tx.id]?.length" class="order-items"><span v-for="item in itemsByTransaction[tx.id]" :key="item.id">{{ item.product_name }}·{{ item.variant }} × {{ item.quantity }}</span></div><div class="tx-foot"><span>余额 ¥{{ money(tx.balance_before) }} → ¥{{ money(tx.balance_after) }}</span><button v-if="tx.transaction_type !== 'reversal' && !reversedIds.has(tx.id)" @click="requestReversal(tx)">冲正</button></div>
      </article></div></section>
    </aside></div>
  </div>
</template>

<style scoped>
.member-page{max-width:1380px;margin:auto;padding:42px 32px 80px}.member-hero{min-height:230px;position:relative;display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:22px;padding:34px;border-radius:22px;overflow:hidden;background:#173d34;color:white}.member-hero>img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:.56}.member-hero:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,#102f2be8 0%,#102f2ba8 48%,#102f2b1f 100%)}.hero-copy,.hero-actions{position:relative;z-index:1}.member-hero h1{font-family:Georgia,"Songti SC",serif;font-size:52px;margin:7px 0 4px;letter-spacing:-2px}.member-hero p{margin:0;color:#dbe5df}.hero-actions{display:flex;gap:9px}.catalog-btn{border:1px solid #ffffff6b;background:#102f2b99;color:white;border-radius:12px;padding:12px 17px;font-weight:700}button{cursor:pointer}.primary-btn{border:0;background:var(--green);color:white;border-radius:12px;padding:13px 20px;font-weight:700;box-shadow:0 8px 22px #174f4226}.member-hero .primary-btn{background:var(--lime);color:var(--green)}.primary-btn span{color:var(--lime);font-size:20px}.member-hero .primary-btn span{color:var(--green)}.primary-btn:disabled,.danger-btn:disabled{opacity:.55;cursor:not-allowed}.notice{display:flex;align-items:center;gap:10px;background:#fff2e7;border:1px solid #eec9a7;color:#8b3b14;padding:12px 15px;border-radius:12px;margin-bottom:18px}.notice>span{display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:#c45f2c;color:white;font-weight:800}.notice button{margin-left:auto;border:0;background:none;font-size:20px}.stats-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:12px}.stats-grid article{position:relative;background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:20px;overflow:hidden}.stats-grid article:first-child{background:var(--green);color:white}.stats-grid article:first-child:after{content:"◎";position:absolute;right:-5px;bottom:-24px;font-size:80px;color:#ffffff12}.stats-grid span,.stats-grid small{display:block;color:var(--muted);font-size:12px}.stats-grid article:first-child span,.stats-grid article:first-child small{color:#d9e6dc}.stats-grid strong{display:block;font-family:Georgia,serif;font-size:25px;margin:10px 0 4px}.insight-strip{display:flex;align-items:center;justify-content:space-between;gap:20px;background:#e9efd9;border:1px solid #d4dec0;border-radius:14px;padding:12px 18px;margin-bottom:20px}.insight-strip>div{display:flex;align-items:center;gap:10px}.insight-icon{font-size:22px;color:#a34f2f}.insight-strip p{margin:0}.insight-strip small,.insight-strip b{display:block}.insight-strip small{color:var(--muted);font-size:10px}.insight-strip>p{font-size:11px;color:var(--muted)}.insight-strip strong{font-size:12px;color:var(--green)}.members-card{background:var(--paper);border:1px solid var(--line);border-radius:18px;overflow:hidden}.table-head{display:flex;justify-content:space-between;align-items:center;padding:22px 24px;border-bottom:1px solid var(--line)}.table-head h2{font-size:19px;margin:0 0 4px}.table-head p{margin:0;color:var(--muted);font-size:12px}.search{width:min(360px,45%);height:42px;display:flex;align-items:center;gap:9px;border:1px solid var(--line);border-radius:12px;padding:0 13px;background:#f8f6ef}.search span{font-size:22px;color:var(--muted)}.search input{width:100%;border:0;outline:0;background:transparent}.table-scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:800px}th{text-align:left;padding:13px 20px;background:#f7f5ee;color:var(--muted);font-size:12px;font-weight:600}td{padding:16px 20px;border-top:1px solid #ebece5;font-size:14px}tbody tr{cursor:pointer;transition:.15s}tbody tr:hover,tbody tr:focus{background:#f4f7ed;outline:0}.member-cell{display:flex;align-items:center;gap:12px}.member-cell>span,.avatar-large{display:grid;place-items:center;border-radius:12px;background:#e3edcf;color:var(--green);font-weight:800}.member-cell>span{width:38px;height:38px}.member-cell b,.member-cell small{display:block}.member-cell small{color:var(--muted);font-size:12px;margin-top:3px}.member-status{font-style:normal;font-weight:600;font-size:9px;border-radius:99px;padding:3px 6px;margin-left:5px;background:#eeeee8;color:#68736e}.member-status.active{background:#daf0d7;color:#277147}.member-status.new{background:#e5edca;color:#5b7226}.member-status.sleep{background:#f6dfd7;color:#9e4a30}.balance{font-weight:800;color:var(--green)}.arrow{font-size:25px;color:#99a29d}.state{text-align:center;padding:70px;color:var(--muted)}.empty b{display:block;font-size:44px;color:#afba9d}.empty h3{color:var(--ink);margin:10px}.empty p{margin:0}.modal-layer,.drawer-layer{position:fixed;inset:0;background:#15201c66;backdrop-filter:blur(3px);z-index:200}.modal-layer{display:grid;place-items:center;padding:20px}.modal{width:min(590px,100%);max-height:90vh;overflow:auto;background:var(--paper);border-radius:20px;box-shadow:0 28px 70px #10201b40}.modal header,.drawer-head{display:flex;align-items:center;padding:22px 26px;border-bottom:1px solid var(--line)}.modal header{justify-content:space-between}.modal header small{color:var(--green);letter-spacing:2px}.modal h2{margin:4px 0 0}.modal header button,.close,.panel-title button{border:0;background:none;font-size:26px;color:var(--muted)}.modal form{padding:24px 26px}.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:15px}.modal label,.action-panel label,.drawer-section label{display:block;font-size:12px;font-weight:700;color:#4d5b56;margin-bottom:15px}.modal input,.modal textarea,.action-panel input,.drawer-section input,.drawer-section textarea{width:100%;border:1px solid var(--line);background:white;border-radius:10px;padding:11px 12px;outline:none;margin-top:7px}.modal input:focus,.modal textarea:focus,.action-panel input:focus,.drawer-section input:focus,.drawer-section textarea:focus{border-color:var(--green);box-shadow:0 0 0 3px #174f4214}.modal textarea,.drawer-section textarea{resize:vertical;min-height:76px}.money-input{position:relative}.money-input span{position:absolute;left:12px;top:18px;color:var(--muted)}.money-input input{padding-left:28px}.modal footer{display:flex;justify-content:flex-end;gap:10px;margin-top:10px}.ghost-btn{border:1px solid var(--line);background:white;border-radius:12px;padding:12px 18px}.catalog-modal{width:min(760px,100%)}.catalog-lead{font-size:12px;color:var(--muted);line-height:1.7;margin:0 0 16px}.catalog-list{display:grid;gap:9px}.catalog-list article{display:grid;grid-template-columns:64px 1fr 120px 72px;align-items:center;gap:12px;border:1px solid var(--line);border-radius:12px;padding:9px}.catalog-list img{width:64px;height:52px;object-fit:cover;border-radius:9px}.catalog-list b,.catalog-list span{display:block}.catalog-list span{font-size:11px;color:var(--muted);margin-top:4px}.catalog-price{margin:0!important}.switch{margin:0!important;text-align:center}.switch input{display:none}.switch i{display:block;width:34px;height:19px;border-radius:99px;background:#c8ccc6;margin:auto;position:relative}.switch i:after{content:"";position:absolute;width:15px;height:15px;border-radius:50%;background:white;left:2px;top:2px;transition:.2s}.switch input:checked+i{background:var(--green)}.switch input:checked+i:after{left:17px}.drawer-layer{display:flex;justify-content:flex-end}.drawer{height:100%;width:min(680px,100%);background:#f8f6ef;overflow:auto;box-shadow:-18px 0 60px #10201b33}.drawer-head{background:var(--paper);gap:13px}.close{margin-right:2px}.avatar-large{width:48px;height:48px;font-size:20px}.drawer-head h2{margin:0 0 5px;font-size:21px}.drawer-head p{margin:0;color:var(--muted);font-size:12px}.drawer-balance{background:var(--green);color:white;margin:18px;border-radius:18px;padding:23px}.drawer-balance>span{font-size:12px;color:#d5e3d9}.drawer-balance>strong{display:block;font-family:Georgia,serif;font-size:38px;margin:7px 0 18px}.drawer-balance>div{display:flex;gap:10px}.drawer-balance button{flex:1;border:1px solid #ffffff45;background:#ffffff12;color:white;border-radius:10px;padding:11px;font-weight:700}.drawer-balance button:last-child{background:var(--lime);border-color:var(--lime);color:var(--green)}.mini-stats{display:grid;grid-template-columns:repeat(3,1fr);margin:0 18px 10px;background:var(--paper);border:1px solid var(--line);border-radius:14px}.mini-stats div{padding:15px;border-right:1px solid var(--line)}.mini-stats div:last-child{border:0}.mini-stats span,.mini-stats b{display:block}.mini-stats span{font-size:11px;color:var(--muted);margin-bottom:7px}.mini-stats b{font-size:14px}.preference-card{display:flex;align-items:center;gap:9px;margin:0 18px 10px;padding:11px 14px;background:#f0eadc;border-radius:11px}.preference-card span{font-size:10px;color:#8b704b}.preference-card b{font-size:12px}.preference-card small{margin-left:auto;color:var(--muted);font-size:10px}.memory-card{display:grid;grid-template-columns:35px 1fr auto;align-items:center;gap:10px;margin:0 18px 18px;padding:13px;background:#e5eed8;border:1px solid #cfddbd;border-radius:13px}.memory-icon{display:grid;place-items:center;width:35px;height:35px;border-radius:10px;background:var(--green);color:var(--lime)}.memory-card span,.memory-card b,.memory-card small{display:block}.memory-card span{font-size:9px;letter-spacing:1px;color:var(--green);font-weight:800}.memory-card b{font-size:12px;margin:3px 0}.memory-card small{font-size:10px;color:var(--muted)}.memory-card>button{border:1px solid #8ea876;background:white;color:var(--green);border-radius:9px;padding:8px 10px;font-size:11px;font-weight:800}.memory-card.sleep{background:#f5e7df;border-color:#e8cbbd}.action-panel,.drawer-section{margin:0 18px 18px;background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px}.action-panel{border-color:#9bb58b}.panel-title,.section-title{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}.panel-title small{display:block;color:var(--muted);font-size:10px;margin-top:3px}.action-panel label{margin-bottom:12px}.panel-title button{font-size:20px}.full{width:100%}.product-picker{display:grid;grid-template-columns:1fr 1fr;gap:9px}.product-picker article{display:grid;grid-template-columns:66px 1fr;position:relative;border:1px solid var(--line);border-radius:12px;padding:8px;min-height:83px}.product-picker article.picked{border-color:#71935d;background:#f2f7e9}.product-picker img{width:58px;height:58px;object-fit:cover;border-radius:9px}.product-info b,.product-info span,.product-info strong{display:block}.product-info b{font-size:12px}.product-info span{font-size:10px;color:var(--muted);margin:2px 0}.product-info strong{font-size:12px;color:#a4502c}.stepper{position:absolute;bottom:6px;right:7px;display:flex;align-items:center;gap:5px}.stepper button{width:23px;height:23px;border:1px solid var(--line);background:white;border-radius:7px;padding:0}.stepper em{font-style:normal;font-size:11px;min-width:12px;text-align:center}.pairing-tip{display:flex;width:100%;align-items:center;gap:6px;border:1px dashed #c9a36d;background:#fff7e8;color:#72532e;border-radius:10px;padding:9px;margin-top:9px;font-size:10px;text-align:left}.pairing-tip span{background:#b66b34;color:white;border-radius:99px;padding:3px 6px}.pairing-tip b{margin-left:auto}.order-fields{margin-top:12px}.order-total{display:flex;justify-content:space-between;align-items:center;border-top:1px dashed var(--line);padding:13px 0}.order-total span{font-size:11px;color:var(--muted)}.order-total b{font-size:17px}.danger-panel{border-color:#d8a599}.danger-panel p{font-size:12px;color:var(--muted)}.danger-btn{border:0;background:#a63e2d;color:white;border-radius:11px;padding:12px;font-weight:700}.drawer-section h3{font-size:15px;margin:0}.text-btn{border:0;background:none;padding:0;color:var(--green);font-weight:800}.section-title span{font-size:11px;color:var(--muted)}.small-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px}.timeline article{position:relative;padding:0 0 18px 22px;border-left:1px solid #d7dbd1;margin-left:5px}.timeline article:last-child{padding-bottom:0}.timeline article>i{position:absolute;width:11px;height:11px;border-radius:50%;background:#7b9e63;left:-6px;top:4px;border:2px solid var(--paper)}.timeline article.consume>i{background:#c8783f}.timeline article.reversal>i{background:#8b8f8d}.timeline article.reversed{opacity:.55}.tx-main,.tx-foot{display:flex;justify-content:space-between;gap:12px}.tx-main b{font-size:13px}.tx-main em{font-style:normal;font-size:10px;background:#e2e4df;border-radius:99px;padding:3px 6px;margin-left:6px}.tx-main small{display:block;color:var(--muted);font-size:11px;margin-top:5px}.tx-main strong{font-size:14px}.order-items{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}.order-items span{font-size:10px;background:#f1eee4;border-radius:6px;padding:4px 6px}.positive{color:#24704f}.negative{color:#a04c32}.tx-foot{margin-top:8px;color:var(--muted);font-size:10px}.tx-foot button{border:0;background:none;color:#9f4635;padding:0}.drawer-section input:disabled{background:#f0f0ec;color:#8c9691}
@media(max-width:1000px){.stats-grid{grid-template-columns:repeat(3,1fr)}.member-page{padding:30px 18px 60px}}
@media(max-width:640px){.member-hero{min-height:280px;align-items:flex-start;padding:24px;flex-direction:column}.member-hero:after{background:linear-gradient(180deg,#102f2be8 0%,#102f2b80 60%,#102f2bd9 100%)}.member-hero h1{font-size:38px}.member-hero p{font-size:13px;max-width:240px}.hero-actions{width:100%;margin-top:auto}.hero-actions button{flex:1}.primary-btn{padding:11px 13px}.stats-grid{grid-template-columns:1fr 1fr}.stats-grid article{padding:16px}.stats-grid article:nth-child(3){grid-column:span 2}.insight-strip{align-items:flex-start}.insight-strip>p{display:none}.table-head{align-items:flex-start;gap:14px;flex-direction:column}.search{width:100%}.modal-layer{padding:0}.modal{height:100%;max-height:none;border-radius:0}.form-grid{grid-template-columns:1fr}.catalog-list article{grid-template-columns:54px 1fr 92px}.catalog-list img{width:52px;height:48px}.catalog-list .switch{grid-column:2/4;display:flex;align-items:center;gap:7px}.catalog-list .switch i{margin:0}.drawer{width:100%}.drawer-head{padding:16px}.drawer-balance{margin:12px}.mini-stats{margin:0 12px 10px}.preference-card,.memory-card{margin:0 12px 10px}.memory-card{grid-template-columns:35px 1fr}.memory-card>button{grid-column:2;width:max-content}.action-panel,.drawer-section{margin:0 12px 12px}.mini-stats b{font-size:12px}.product-picker{grid-template-columns:1fr}.member-page{padding-top:24px}}
</style>
