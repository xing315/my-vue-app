<script>
import { supabase } from './supabase.js'

const LABELS = { startup:'启动', method:'方法', page_resume:'页面进入', page_pause:'页面离开', click:'点击', block:'卡顿', aop_enter:'AOP 进入', aop_exit:'AOP 退出' }
const COLORS = { startup:'#c8f560', method:'#74b9a8', page_resume:'#65a9ff', page_pause:'#91a09c', click:'#ffb45e', block:'#ef7354', aop_enter:'#b896ff', aop_exit:'#9f7aea' }

export default {
  data: () => ({ loading:true, error:'', events:[], typeFilter:'all', appFilter:'all', range:'24h', lastUpdated:null, timer:null }),
  computed: {
    cutoff() {
      const hours = this.range === '1h' ? 1 : this.range === '7d' ? 168 : 24
      return new Date(Date.now() - hours * 3600_000)
    },
    rangeEvents() { return this.events.filter(e => new Date(e.event_time) >= this.cutoff) },
    apps() { return [...new Set(this.rangeEvents.map(e => e.app_id).filter(Boolean))].sort() },
    eventTypes() { return [...new Set(this.rangeEvents.map(e => e.event_type))].sort() },
    filteredEvents() {
      return this.rangeEvents.filter(e => (this.typeFilter === 'all' || e.event_type === this.typeFilter) && (this.appFilter === 'all' || e.app_id === this.appFilter))
    },
    launches() { return this.filteredEvents.filter(e => e.event_type === 'startup') },
    avgStartup() {
      const values = this.launches.map(e => Number(e.cost_ms)).filter(Number.isFinite)
      return values.length ? Math.round(values.reduce((a,b) => a + b, 0) / values.length) : null
    },
    slowCount() {
      return this.filteredEvents.filter(e => e.event_type === 'block' || (['method','aop_exit'].includes(e.event_type) && Number(e.cost_ms) >= 100)).length
    },
    uniqueDevices() { return new Set(this.filteredEvents.map(e => e.device_id).filter(Boolean)).size },
    chartBuckets() {
      const count = this.range === '7d' ? 7 : 12
      const span = (Date.now() - this.cutoff.getTime()) / count
      const buckets = Array.from({ length:count }, (_,i) => ({ start:this.cutoff.getTime() + i * span, count:0 }))
      this.filteredEvents.forEach(e => {
        const i = Math.min(count - 1, Math.max(0, Math.floor((new Date(e.event_time).getTime() - this.cutoff.getTime()) / span)))
        if (buckets[i]) buckets[i].count++
      })
      const max = Math.max(1, ...buckets.map(b => b.count))
      return buckets.map(b => ({ ...b, height:Math.max(4, b.count / max * 100), label:this.range === '7d' ? new Date(b.start).toLocaleDateString('zh-CN',{month:'numeric',day:'numeric'}) : new Date(b.start).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit'}) }))
    },
    typeSummary() {
      const counts = {}
      this.filteredEvents.forEach(e => { counts[e.event_type] = (counts[e.event_type] || 0) + 1 })
      return Object.entries(counts).sort((a,b) => b[1] - a[1])
    }
  },
  watch: { range() { this.fetchEvents() } },
  mounted() { this.fetchEvents(); this.timer = window.setInterval(this.fetchEvents, 30_000) },
  beforeUnmount() { window.clearInterval(this.timer) },
  methods: {
    async fetchEvents() {
      this.error = ''
      try {
        const { data: { session } } = await supabase.auth.getSession()
        if (!session) throw new Error('authentication_required')
        const { data, error } = await supabase.from('app_telemetry_events')
          .select('id,event_type,event_time,received_at,app_id,app_version,device_id,session_id,page,method,view_type,view_id,cost_ms,tag,permission,allowed,metadata')
          .gte('event_time', this.cutoff.toISOString()).order('event_time',{ascending:false}).limit(2000)
        if (error) throw error
        this.events = data || []
        this.lastUpdated = new Date()
      } catch (e) {
        this.error = e.message === 'authentication_required'
          ? '埋点数据包含设备与性能信息，请先登录后查看。'
          : e.message?.includes('app_telemetry_events') ? '数据表尚未创建，请先执行项目中的 Supabase 迁移。' : `读取数据失败：${e.message || '请稍后重试'}`
      } finally { this.loading = false }
    },
    label(type) { return LABELS[type] || type },
    color(type) { return COLORS[type] || '#174f42' },
    title(e) { return e.page || e.method || e.view_id || e.tag || this.label(e.event_type) },
    detail(e) {
      const list = []
      if (e.view_type) list.push(e.view_type)
      if (e.cost_ms != null) list.push(`${Number(e.cost_ms).toFixed(1)} ms`)
      if (e.app_version) list.push(`v${e.app_version}`)
      return list.join(' · ') || e.app_id
    },
    formatTime(value) { return new Date(value).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}) },
    resetFilters() { this.typeFilter = 'all'; this.appFilter = 'all' }
  }
}
</script>

<template>
  <div class="telemetry-page">
    <header class="hero">
      <div><p class="eyebrow">APP TELEMETRY / LIVE</p><h1>应用数据观测台</h1><p>汇集字节码插装产生的启动、页面、点击、方法耗时与卡顿数据。</p></div>
      <div class="live-state"><span class="pulse"></span><div><b>自动刷新</b><small>{{ lastUpdated ? `更新于 ${lastUpdated.toLocaleTimeString('zh-CN')}` : '正在连接数据源' }}</small></div><button @click="fetchEvents" :disabled="loading">刷新</button></div>
    </header>

    <section class="toolbar">
      <div class="range-tabs"><button v-for="item in [{id:'1h',label:'近 1 小时'},{id:'24h',label:'近 24 小时'},{id:'7d',label:'近 7 天'}]" :key="item.id" :class="{active:range===item.id}" @click="range=item.id">{{ item.label }}</button></div>
      <label>应用 <select v-model="appFilter"><option value="all">全部应用</option><option v-for="app in apps" :key="app">{{ app }}</option></select></label>
      <label>事件 <select v-model="typeFilter"><option value="all">全部事件</option><option v-for="type in eventTypes" :key="type" :value="type">{{ label(type) }}</option></select></label>
    </section>

    <div v-if="error" class="state-card"><strong>暂时无法展示埋点数据</strong><p>{{ error }}</p><button @click="fetchEvents">重新连接</button></div>
    <div v-else-if="loading" class="state-card loading"><span></span><p>正在聚合 App 埋点数据…</p></div>
    <template v-else>
      <section class="metric-grid">
        <article><i class="metric-icon lime">↗</i><span>事件总量</span><strong>{{ filteredEvents.length.toLocaleString() }}</strong><small>当前筛选时间范围</small></article>
        <article><i class="metric-icon blue">◉</i><span>独立设备</span><strong>{{ uniqueDevices.toLocaleString() }}</strong><small>按匿名安装 ID 去重</small></article>
        <article><i class="metric-icon orange">⚡</i><span>平均启动耗时</span><strong>{{ avgStartup == null ? '—' : `${avgStartup}ms` }}</strong><small>{{ launches.length }} 次启动样本</small></article>
        <article><i class="metric-icon red">!</i><span>慢方法 / 卡顿</span><strong>{{ slowCount.toLocaleString() }}</strong><small>方法 ≥100ms 或主线程卡顿</small></article>
      </section>

      <section class="main-grid">
        <article class="panel trend"><div class="panel-head"><div><span>事件趋势</span><h2>数据上报量</h2></div><b>{{ filteredEvents.length }} events</b></div>
          <div v-if="filteredEvents.length" class="chart"><div v-for="b in chartBuckets" :key="b.start" class="bar-wrap" :title="`${b.label}: ${b.count}`"><em>{{ b.count }}</em><i :style="{height:`${b.height}%`}"></i><small>{{ b.label }}</small></div></div>
          <div v-else class="mini-empty">当前筛选范围内还没有事件</div>
        </article>
        <article class="panel types"><div class="panel-head"><div><span>事件构成</span><h2>埋点类型</h2></div></div>
          <div v-if="typeSummary.length" class="type-list"><div v-for="[type,count] in typeSummary.slice(0,6)" :key="type"><i :style="{background:color(type)}"></i><b>{{ label(type) }}</b><span><em :style="{width:`${Math.max(5,count/filteredEvents.length*100)}%`,background:color(type)}"></em></span><strong>{{ count }}</strong></div></div>
          <div v-else class="mini-empty">暂无构成数据</div>
        </article>
      </section>

      <section class="panel stream">
        <div class="panel-head"><div><span>实时事件流</span><h2>最近上报</h2></div><button v-if="typeFilter!=='all'||appFilter!=='all'" @click="resetFilters">清除筛选</button></div>
        <div v-if="filteredEvents.length" class="event-table">
          <div class="table-row table-head"><span>类型</span><span>事件对象</span><span>应用</span><span>设备 / 会话</span><span>发生时间</span></div>
          <div class="table-row" v-for="e in filteredEvents.slice(0,50)" :key="e.id">
            <span><i :style="{background:color(e.event_type)}"></i>{{ label(e.event_type) }}</span>
            <span><b>{{ title(e) }}</b><small>{{ detail(e) }}</small></span>
            <span><b>{{ e.app_id }}</b><small>{{ e.app_version ? `版本 ${e.app_version}` : '版本未知' }}</small></span>
            <span><code>{{ e.device_id?.slice(0,10) || 'anonymous' }}</code><small>{{ e.session_id?.slice(0,10) || '无会话标识' }}</small></span>
            <span>{{ formatTime(e.event_time) }}</span>
          </div>
        </div>
        <div v-else class="empty"><div>⌁</div><h3>等待第一批埋点数据</h3><p>App 配置上报接口并产生事件后，启动、页面访问和性能数据会出现在这里。</p></div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.telemetry-page{max-width:1280px;margin:auto;padding:46px 28px 80px}.hero{display:flex;align-items:flex-end;justify-content:space-between;gap:32px;margin-bottom:30px}.hero h1{font:clamp(38px,5vw,66px)/1.05 Georgia,"Songti SC";letter-spacing:-2px;margin:9px 0 12px}.hero>div>p:last-child{color:var(--muted)}.live-state{display:flex;align-items:center;gap:11px;background:var(--paper);border:1px solid var(--line);border-radius:15px;padding:12px 14px;min-width:285px}.live-state b,.live-state small{display:block}.live-state b{font-size:13px}.live-state small{color:var(--muted);font-size:10px;margin-top:3px}.live-state button,.stream button{margin-left:auto;border:1px solid var(--line);background:white;border-radius:9px;padding:7px 11px;cursor:pointer}.pulse{width:9px;height:9px;background:#62c977;border-radius:50%;box-shadow:0 0 0 5px #62c97720}
.toolbar{display:flex;align-items:center;gap:12px;border-top:1px solid var(--line);padding-top:18px;margin-bottom:18px}.range-tabs{display:flex;background:#e8e8df;border-radius:10px;padding:3px;margin-right:auto}.range-tabs button{border:0;background:transparent;border-radius:8px;padding:8px 13px;font-size:12px;cursor:pointer}.range-tabs button.active{background:var(--paper);box-shadow:0 1px 4px #16201d18;color:var(--green);font-weight:700}.toolbar label{font-size:11px;color:var(--muted)}.toolbar select{border:1px solid var(--line);background:var(--paper);border-radius:9px;padding:8px;color:var(--ink)}
.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}.metric-grid article,.panel{background:var(--paper);border:1px solid var(--line);border-radius:18px}.metric-grid article{padding:21px;position:relative}.metric-grid span,.panel-head span{font-size:11px;color:var(--muted)}.metric-grid strong{display:block;font:31px Georgia;margin:16px 0 5px}.metric-grid small{color:var(--muted);font-size:10px}.metric-icon{font-style:normal;position:absolute;right:18px;top:18px;width:32px;height:32px;border-radius:9px;display:grid;place-content:center}.lime{background:#e4f9b8}.blue{background:#dceeff}.orange{background:#ffe7c7}.red{background:#ffe0d9}
.main-grid{display:grid;grid-template-columns:1.7fr .7fr;gap:14px;margin-bottom:14px}.panel{padding:23px}.panel-head{display:flex;justify-content:space-between}.panel-head h2{font:23px Georgia;margin:6px 0}.panel-head>b{font:12px monospace;color:var(--green);background:#e6f0e5;padding:8px;border-radius:8px}.chart{height:250px;display:flex;align-items:end;gap:7px;padding:37px 0 27px;border-bottom:1px solid var(--line)}.bar-wrap{height:100%;flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;position:relative}.bar-wrap>i{width:70%;max-width:42px;background:linear-gradient(#276d5c,#174f42);border-radius:6px 6px 2px 2px;min-height:4px}.bar-wrap small{position:absolute;top:calc(100% + 9px);font-size:9px;color:var(--muted)}.bar-wrap em{font:9px monospace;color:var(--muted);font-style:normal}.mini-empty{height:230px;display:grid;place-content:center;color:var(--muted);font-size:12px}.type-list{margin-top:26px}.type-list>div{display:grid;grid-template-columns:8px 68px 1fr 28px;align-items:center;gap:8px;margin:17px 0}.type-list>div>i,.table-row>span:first-child i{width:7px;height:7px;border-radius:50%}.type-list b{font-size:12px}.type-list span{height:5px;background:#ecece5;border-radius:5px;overflow:hidden}.type-list span em{display:block;height:100%}
.event-table{margin-top:10px}.table-row{display:grid;grid-template-columns:120px minmax(230px,1.7fr) minmax(120px,.8fr) minmax(140px,1fr) 150px;gap:14px;align-items:center;border-top:1px solid #e7e8e1;padding:13px 6px;font-size:12px}.table-row>span:first-child{display:flex;align-items:center;gap:8px}.table-row b,.table-row small{display:block}.table-row b{font-size:12px;overflow:hidden;text-overflow:ellipsis}.table-row small{font-size:9px;color:var(--muted);margin-top:4px}.table-head{color:var(--muted);font-size:9px}.empty,.state-card{text-align:center;padding:70px 24px}.empty div{font-size:38px;color:var(--green)}.empty h3,.state-card strong{font:22px Georgia}.empty p,.state-card p{color:var(--muted)}.state-card{background:var(--paper);border:1px solid var(--line);border-radius:18px}.state-card button{border:0;background:var(--green);color:white;border-radius:10px;padding:10px 16px}.loading span{display:block;width:30px;height:30px;margin:auto;border:3px solid var(--line);border-top-color:var(--green);border-radius:50%;animation:spin 1s linear infinite}
@media(max-width:900px){.telemetry-page{padding:30px 18px 60px}.hero{align-items:start;flex-direction:column}.live-state{width:100%}.metric-grid{grid-template-columns:1fr 1fr}.main-grid{grid-template-columns:1fr}.event-table{overflow-x:auto}.table-row{min-width:850px}.toolbar{flex-wrap:wrap}.range-tabs{width:100%;margin:0}.range-tabs button{flex:1}}@media(max-width:520px){.metric-grid{grid-template-columns:1fr}}
</style>
