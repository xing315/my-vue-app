<script>
import { supabase } from './supabase.js'

const chartShardCache = new Map()

function chartStats(bars) {
  const closes=bars.map(b=>b.close).filter(Number.isFinite)
  if(!closes.length) return {}
  let peak=closes[0], maxDrawdown=0
  const returns=[]
  for(let i=0;i<closes.length;i++) { peak=Math.max(peak,closes[i]); maxDrawdown=Math.min(maxDrawdown,closes[i]/peak-1); if(i) returns.push(closes[i]/closes[i-1]-1) }
  const recent=returns.slice(-250), mean=recent.reduce((a,b)=>a+b,0)/Math.max(recent.length,1)
  const variance=recent.reduce((a,b)=>a+(b-mean)**2,0)/Math.max(recent.length-1,1)
  const amounts=bars.slice(-20).map(b=>b.amount).filter(Number.isFinite)
  return {startDate:bars[0].date,endDate:bars.at(-1).date,tradingDays:bars.length,
    periodReturn:closes.at(-1)/closes[0]-1,return1y:closes.at(-1)/closes[Math.max(0,closes.length-240)]-1,
    maxDrawdown,annualVolatility:Math.sqrt(variance)*Math.sqrt(250),
    high:Math.max(...bars.map(b=>b.high).filter(Number.isFinite)),low:Math.min(...bars.map(b=>b.low).filter(Number.isFinite)),
    averageAmount20:amounts.reduce((a,b)=>a+b,0)/Math.max(amounts.length,1)}
}

function addMovingAverages(bars) {
  for(const days of [5,20,60,120,250]) for(let i=0;i<bars.length;i++) {
    if(i+1<days) bars[i][`ma${days}`]=null
    else bars[i][`ma${days}`]=bars.slice(i-days+1,i+1).reduce((sum,row)=>sum+row.close,0)/days
  }
  return bars
}

const DEMO = {
  mode: 'demo', updatedAt: '2026-08-01T15:30:00+08:00', modelVersion: 'cn-equity-v1.0',
  market: { indices: [{name:'上证指数',value:'3,559.95',change:0.42},{name:'沪深300',value:'4,181.73',change:0.31},{name:'中证500',value:'6,442.18',change:-0.18}], breadth: 56, valuation: 47, risk: '中性' },
  stocks: [
    {code:'600036',name:'招商银行',industry:'银行',price:46.72,change:0.86,score:84,confidence:91,quality:23,growth:15,valuation:18,trend:12,risk:8,liquidity:8,position:[4,6],pe:7.1,pb:1.12,reportDate:'2026-04-29',reason:'盈利质量与资本充足率优于行业中位数，估值仍处历史中低区间。',counter:'净息差若持续收窄，当前盈利预期可能下修。',flags:[]},
    {code:'000333',name:'美的集团',industry:'家用电器',price:81.36,change:-0.22,score:79,confidence:87,quality:22,growth:16,valuation:14,trend:11,risk:8,liquidity:8,position:[3,5],pe:14.8,pb:3.25,reportDate:'2026-04-30',reason:'经营现金流稳定，海外业务与股东回报对中长期估值形成支撑。',counter:'海外需求、汇率与原材料价格可能压缩利润率。',flags:[]},
    {code:'600519',name:'贵州茅台',industry:'白酒',price:1488.20,change:1.04,score:73,confidence:83,quality:24,growth:14,valuation:11,trend:9,risk:8,liquidity:7,position:[3,4],pe:21.5,pb:7.4,reportDate:'2026-04-28',reason:'品牌壁垒、现金流和盈利稳定性突出，但估值安全边际仅属中等。',counter:'批价与需求走弱会使高质量溢价下降。',flags:[]},
    {code:'300750',name:'宁德时代',industry:'电池',price:263.40,change:-1.38,score:68,confidence:78,quality:18,growth:15,valuation:13,trend:8,risk:6,liquidity:8,position:[2,4],pe:19.7,pb:4.1,reportDate:'2026-04-25',reason:'行业地位和研发能力较强，估值较历史高位回落。',counter:'产能竞争、价格下行与海外政策是主要压力。',flags:['高波动']},
    {code:'002594',name:'比亚迪',industry:'汽车',price:112.68,change:-2.11,score:52,confidence:74,quality:16,growth:14,valuation:8,trend:6,risk:4,liquidity:4,position:[0,2],pe:24.3,pb:5.2,reportDate:'2026-04-27',reason:'销量规模与产业链整合仍有优势。',counter:'价格战、资本开支与行业库存使风险收益比偏弱。',flags:['估值压力','行业竞争']},
    {code:'600777',name:'演示风险股',industry:'综合',price:3.18,change:-4.79,score:25,confidence:35,quality:5,growth:4,valuation:6,trend:2,risk:2,liquidity:6,position:[0,0],pe:null,pb:5.8,reportDate:'2026-04-30',reason:'暂无足够基本面证据支持中长线配置。',counter:'审计意见与持续经营指标异常，触发严格过滤。',flags:['硬性排除','数据不足']}
  ],
  validation: {annualReturn:12.8,maxDrawdown:-17.4,winRate:58.2,excessReturn:4.1,period:'2016–2025 滚动窗口'},
  sources: [{name:'BaoStock',state:'ready',detail:'历史日线·演示快照'},{name:'AKShare',state:'offline',detail:'后端未连接'},{name:'巨潮资讯',state:'ready',detail:'公告日期·演示快照'}]
}

export default {
  props: { user: Object },
  data: () => ({ data:null, loading:true, query:'', industry:'all', minScore:0, selected:null, stockDetail:null, detailLoading:false, detailError:'', chartWindow:120, budget:100000, holdings:[], form:{code:'',name:'',cost:'',shares:''}, tab:'top30', error:'', demo:false, coverageCount:0 }),
  computed: {
    stocks() { return this.data?.stocks || [] },
    industries() { return [...new Set(this.stocks.map(s=>s.industry))] },
    filtered() { const q=this.query.trim().toLowerCase(); return this.stocks.filter(s=>(!q||s.code.includes(q)||s.name.toLowerCase().includes(q))&&(this.industry==='all'||s.industry===this.industry)&&s.score>=this.minScore).slice(0,200) },
    selectedStock() { return this.selected || this.filtered[0] || this.stocks[0] },
    dailyRecommendations() { return (this.data?.recommendations||this.stocks.map(s=>s.recommendation).filter(Boolean)).slice().sort((a,b)=>a.rank-b.rank) },
    quantity() { const s=this.selectedStock; if(!s||!this.budget||!s.position[1]) return 0; const ratio=(s.position[0]+s.position[1])/2/100; return Math.floor((this.budget*ratio/s.price)/100)*100 },
    invested() { return this.quantity*(this.selectedStock?.price||0) },
    portfolio() { return this.holdings.map(h=>{ const s=this.stocks.find(x=>x.code===h.code); const price=s?.price||h.cost; return {...h,price,value:price*h.shares,pnl:(price-h.cost)*h.shares,score:s?.score} }) },
    totalValue() { return this.portfolio.reduce((n,h)=>n+h.value,0) },
    breadthStyle() { return {width:`${this.data?.market.breadth||0}%`} },
    latestFinancial() { return this.stockDetail?.financials?.[0] || null },
    chart() {
      const rows=(this.stockDetail?.bars||[]).slice(-this.chartWindow)
      if(!rows.length) return null
      const numbers=rows.flatMap(r=>[r.low,r.high,r.ma20,r.ma60]).filter(Number.isFinite)
      const min=Math.min(...numbers), max=Math.max(...numbers), range=Math.max(max-min,.01)
      const y=v=>285-(v-min)/range*255
      const step=860/Math.max(rows.length-1,1), width=Math.max(2,Math.min(7,step*.58))
      const maxVolume=Math.max(...rows.map(r=>Number(r.volume)||0),1)
      const candles=rows.map((r,i)=>({ ...r,x:20+i*step,w:width,yo:y(r.open),yc:y(r.close),yh:y(r.high),yl:y(r.low),
        volumeHeight:(Number(r.volume)||0)/maxVolume*55,up:r.close>=r.open }))
      const line=key=>rows.map((r,i)=>Number.isFinite(r[key])?`${20+i*step},${y(r[key])}`:null).filter(Boolean).join(' ')
      return {candles,ma20:line('ma20'),ma60:line('ma60'),min,max,first:rows[0].date,last:rows.at(-1).date,
        periodReturn:rows.at(-1).close/rows[0].close-1}
    }
  },
  mounted() { this.load(); try { this.holdings=JSON.parse(localStorage.getItem('quant-holdings')||'[]') } catch {} },
  methods: {
    async loadRemoteDetail(symbol) {
      const shard=String(Number(symbol)%64).padStart(2,'0')
      let payload=chartShardCache.get(shard)
      if(!payload) {
        const {data}=supabase.storage.from('quant-stock-charts').getPublicUrl(`v1/shard-${shard}.json.gz`)
        const response=await fetch(data.publicUrl)
        if(!response.ok) throw new Error(`线上图表 HTTP ${response.status}`)
        const compressed=await response.arrayBuffer()
        if(typeof DecompressionStream==='undefined') throw new Error('当前浏览器不支持 gzip 图表解压')
        const stream=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))
        payload=JSON.parse(await new Response(stream).text()); chartShardCache.set(shard,payload)
      }
      const item=payload.stocks?.[symbol]
      if(!item) throw new Error('线上图表分片中没有该股票')
      const bars=addMovingAverages(item.b.map(row=>({date:row[0],open:row[1],high:row[2],low:row[3],close:row[4],volume:row[5],amount:row[6]})))
      return {symbol,bars,financials:item.f?[item.f]:[],stats:chartStats(bars),dataScope:item.scope}
    },
    async loadSupabase() {
      const { data:snapshots, error:snapshotError } = await supabase.from('quant_market_snapshots')
        .select('trade_date,updated_at,model_version,coverage_count,eligible_count,market,validation,sources')
        .order('trade_date',{ascending:false}).limit(1)
      if (snapshotError) throw snapshotError
      const snapshot=snapshots?.[0]
      if (!snapshot) throw new Error('Supabase 尚无已发布的量化快照')
      const { data:rows, error:scoresError } = await supabase.from('quant_latest_scores')
        .select('symbol,name,industry,score,confidence,price,change_percent,position_min,position_max,excluded,detail,trade_date')
        .order('excluded',{ascending:true}).order('score',{ascending:false}).order('confidence',{ascending:false}).limit(1000)
      if (scoresError) throw scoresError
      const stocks=(rows||[]).map(row=>({...row.detail,code:row.symbol,name:row.name,industry:row.industry,
        score:row.score,confidence:row.confidence,price:Number(row.price),change:Number(row.change_percent),
        position:[row.position_min,row.position_max],flags:row.excluded?(row.detail?.flags||['严格过滤']):(row.detail?.flags||[])}))
      this.coverageCount=snapshot.coverage_count
      let recommendations=stocks.map(stock=>stock.recommendation).filter(Boolean)
      const {data:recommendationRows}=await supabase.from('quant_daily_recommendations').select('*')
        .eq('trade_date',snapshot.trade_date).order('rank',{ascending:true}).limit(30)
      if(recommendationRows?.length) recommendations=recommendationRows.map(row=>({rank:row.rank,previousRank:row.previous_rank,
        rankChange:row.rank_change,code:row.symbol,name:row.name,industry:row.industry,score:row.score,confidence:row.confidence,
        price:Number(row.price),change:Number(row.change_percent),position:[row.position_min,row.position_max],explanation:row.explanation}))
      return {mode:'live',updatedAt:snapshot.updated_at,modelVersion:snapshot.model_version,market:snapshot.market,
        validation:snapshot.validation,sources:snapshot.sources,stocks,recommendations}
    },
    async load() {
      this.loading=true; this.error=''
      try {
        let payload
        try { const r=await fetch('/api/quant/dashboard'); if(!r.ok) throw new Error(`API HTTP ${r.status}`); payload=await r.json(); if(payload.mode!=='live') throw new Error('本地 API 无正式快照') }
        catch { payload=await this.loadSupabase() }
        this.data=payload; this.coverageCount=this.coverageCount||payload.stocks?.length||0; this.demo=false
      } catch(e) {
        this.data=DEMO; this.coverageCount=DEMO.stocks.length; this.demo=true
        this.error=`${e.message||'分析服务未连接'}，当前为演示快照，不可用于真实投资决策。`
      } finally { this.loading=false }
    },
    rating(score) { return score>=80?'重点研究':score>=70?'值得关注':score>=55?'中性观察':score>=40?'谨慎':'回避' },
    tone(score) { return score>=80?'strong':score>=70?'good':score>=55?'neutral':score>=40?'warn':'avoid' },
    money(v) { return Number(v||0).toLocaleString('zh-CN',{style:'currency',currency:'CNY',maximumFractionDigits:0}) },
    compactMoney(v) { if(v==null) return '—'; return Number(v).toLocaleString('zh-CN',{notation:'compact',maximumFractionDigits:2}) },
    percent(v) { return v==null?'—':`${v>=0?'+':''}${(Number(v)*100).toFixed(2)}%` },
    metric(v,suffix='') { return v==null?'—':`${Number(v).toFixed(2)}${suffix}` },
    exchange(code) { return code?.startsWith('6')?'上海证券交易所':'深圳证券交易所' },
    time(v) { return new Date(v).toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}) },
    addHolding() { const h={code:this.form.code.trim(),name:this.form.name.trim()||this.form.code.trim(),cost:Number(this.form.cost),shares:Number(this.form.shares)}; if(!h.code||!h.cost||!h.shares) return; this.holdings.push(h); this.save(); this.form={code:'',name:'',cost:'',shares:''} },
    removeHolding(i) { this.holdings.splice(i,1); this.save() },
    save() { localStorage.setItem('quant-holdings',JSON.stringify(this.holdings)) },
    async select(s) {
      this.selected=s; this.tab='detail'; this.stockDetail=null; this.detailError=''; this.detailLoading=true
      window.scrollTo({top:0,behavior:'smooth'})
      try {
        const response=await fetch(`/api/quant/stocks/${s.code}`)
        if(!response.ok) throw new Error(`详情接口 HTTP ${response.status}`)
        this.stockDetail=await response.json()
      } catch(localError) {
        try { this.stockDetail=await this.loadRemoteDetail(s.code) }
        catch(remoteError) { this.detailError=`个股详情暂时不可用：${remoteError.message}。本地可启动 npm run quant:server 查看。` }
      } finally { this.detailLoading=false }
    }
  }
}
</script>

<template>
  <div class="quant-page" v-if="!loading">
    <div v-if="demo" class="demo-banner"><b>DEMO</b><span>{{ error || '当前使用演示快照' }}</span><button @click="load">重新连接</button></div>
    <header class="q-hero">
      <div><p class="eyebrow">QUANT RESEARCH / A-SHARES</p><h1>看清数据，再做决定。</h1><p>面向 3–12 个月周期的 A 股中长线研究看板。只提供分析，不执行交易。</p></div>
      <div class="as-of"><span :class="{demo}"></span><div><small>盘后评级</small><b>{{ time(data.updatedAt) }}</b></div><em>{{ data.modelVersion }}</em></div>
    </header>

    <nav class="q-tabs"><button v-for="t in [{id:'top30',name:'今日前30'},{id:'candidates',name:'市场与候选'},{id:'detail',name:'个股分析'},{id:'portfolio',name:'我的持仓'},{id:'validation',name:'模型与数据'}]" :key="t.id" :class="{active:tab===t.id}" @click="tab=t.id">{{ t.name }}</button></nav>

    <template v-if="tab==='top30'">
      <section class="section-head top-head"><div><span>DAILY TOP 30 / EXPERIMENTAL</span><h2>今日重点研究名单</h2></div><p>规则模型排名 · 行业最多 4 只 · 大模型只解释，不参与评分</p></section>
      <div class="experimental-note"><b>实验性排名</b><span>正式滚动回测尚未完成。本名单用于缩小研究范围，不构成购买建议；请核对最新公告及数据日期。</span></div>
      <section v-if="dailyRecommendations.length" class="recommendation-grid">
        <article v-for="item in dailyRecommendations" :key="item.code" class="recommendation-card">
          <header><i>#{{ item.rank }}</i><div><b>{{ item.name }}</b><span>{{ item.code }} · {{ item.industry }}</span></div><em v-if="item.rankChange" :class="item.rankChange>0?'up':'down'">{{ item.rankChange>0?'↑':'↓' }}{{ Math.abs(item.rankChange) }}</em><em v-else>NEW</em><strong :class="tone(item.score)">{{ item.score }}</strong></header>
          <p>{{ item.explanation?.summary }}</p>
          <ul><li v-for="e in (item.explanation?.positiveEvidence||[]).slice(0,2)" :key="e">{{ e }}</li></ul>
          <div class="rec-risk"><b>主要反证</b><span>{{ item.explanation?.negativeEvidence?.[0] || '等待更多反面证据' }}</span></div>
          <footer><span>置信 {{ item.confidence }}%</span><span>建议仓位 {{ item.position?.[0] }}–{{ item.position?.[1] }}%</span><button @click="select(stocks.find(s=>s.code===item.code)||item)">完整分析 →</button></footer>
        </article>
      </section>
      <div v-else class="empty-q">当前快照尚未生成前 30 名，请在本地运行一次 npm run quant:sync。</div>
    </template>

    <template v-else-if="tab==='candidates'">
      <section class="market-grid">
        <article v-for="i in data.market.indices" :key="i.name"><span>{{ i.name }}</span><b>{{ i.value }}</b><em :class="i.change>=0?'up':'down'">{{ i.change>=0?'+':'' }}{{ i.change }}%</em></article>
        <article class="breadth"><span>上涨宽度</span><b>{{ data.market.breadth }}%</b><div><i :style="breadthStyle"></i></div><small>市场风险：{{ data.market.risk }}</small></article>
      </section>
      <section class="section-head"><div><span>DAILY SCREEN</span><h2>全 A 股盘后筛选</h2></div><p>已覆盖 {{ coverageCount }} 只 · 线上加载高排名候选，列表最多展示 200 只。</p></section>
      <div class="filters"><input v-model="query" placeholder="搜索代码或名称"><select v-model="industry"><option value="all">全部行业</option><option v-for="i in industries" :key="i">{{ i }}</option></select><label>最低评分 <input type="range" v-model.number="minScore" min="0" max="90" step="5"><b>{{ minScore }}</b></label></div>
      <section class="stock-table">
        <div class="s-row s-head"><span>标的</span><span>评级</span><span>最新价</span><span>核心证据</span><span>建议仓位</span><span></span></div>
        <div class="s-row" v-for="s in filtered" :key="s.code">
          <span><b>{{ s.name }}</b><small>{{ s.code }} · {{ s.industry }}</small></span><span><i class="score" :class="tone(s.score)">{{ s.score }}</i><small>{{ rating(s.score) }} · 置信 {{ s.confidence }}%</small></span><span><b>¥{{ s.price.toFixed(2) }}</b><small :class="s.change>=0?'up':'down'">{{ s.change>=0?'+':'' }}{{ s.change }}%</small></span><span><b>{{ s.reason }}</b><small v-if="s.flags.length" class="flags">{{ s.flags.join(' · ') }}</small></span><span><b>{{ s.position[1] ? `${s.position[0]}–${s.position[1]}%` : '不建议' }}</b><small>单股上限 8%</small></span><span><button @click="select(s)">查看分析 →</button></span>
        </div><div v-if="!filtered.length" class="empty-q">当前条件下没有候选股票</div>
      </section>
    </template>

    <template v-else-if="tab==='detail' && selectedStock">
      <section class="detail-hero"><div><span>{{ selectedStock.code }} · {{ selectedStock.industry }}</span><h2>{{ selectedStock.name }}</h2><p>{{ rating(selectedStock.score) }} · 置信度 {{ selectedStock.confidence }}%</p></div><div class="hero-price"><b>¥{{ selectedStock.price.toFixed(2) }}</b><em :class="selectedStock.change>=0?'up':'down'">{{ selectedStock.change>=0?'+':'' }}{{ selectedStock.change }}%</em></div><div class="big-score" :class="tone(selectedStock.score)"><b>{{ selectedStock.score }}</b><span>/ 100</span></div></section>
      <section class="profile-strip">
        <div><span>交易所</span><b>{{ exchange(selectedStock.code) }}</b></div><div><span>所属行业</span><b>{{ selectedStock.industry || '暂缺' }}</b></div>
        <div><span>上市日期</span><b>数据暂未接入</b></div><div><span>行情范围</span><b>{{ stockDetail?.stats?.startDate || '等待本地服务' }} 至 {{ stockDetail?.stats?.endDate || '—' }}</b></div>
      </section>
      <section class="panel-q chart-panel">
        <div class="chart-head"><div><span>PRICE & VOLUME</span><h3>价格趋势与成交量</h3></div><div class="range-buttons"><button v-for="r in [{n:'3月',v:60},{n:'6月',v:120},{n:'1年',v:250},{n:'全部',v:900}]" :key="r.v" :class="{active:chartWindow===r.v}" @click="chartWindow=r.v">{{ r.n }}</button></div></div>
        <div v-if="detailLoading" class="detail-state">正在读取本地行情…</div>
        <div v-else-if="detailError" class="detail-state warning">{{ detailError }}</div>
        <template v-else-if="chart">
          <div class="chart-summary"><span>图示区间涨跌 <b :class="chart.periodReturn>=0?'up':'down'">{{ percent(chart.periodReturn) }}</b></span><span>近一年 <b :class="stockDetail.stats.return1y>=0?'up':'down'">{{ percent(stockDetail.stats.return1y) }}</b></span><span>全数据最大回撤 <b class="down">{{ percent(stockDetail.stats.maxDrawdown) }}</b></span><span>近一年波动 <b>{{ percent(stockDetail.stats.annualVolatility) }}</b></span></div>
          <svg class="stock-chart" viewBox="0 0 900 370" preserveAspectRatio="none" role="img" :aria-label="`${selectedStock.name}价格走势`">
            <line v-for="y in [30,94,158,222,285]" :key="y" x1="20" x2="880" :y1="y" :y2="y" class="grid-line"/>
            <g v-for="c in chart.candles" :key="c.date"><line :x1="c.x" :x2="c.x" :y1="c.yh" :y2="c.yl" :class="c.up?'c-up':'c-down'"/><rect :x="c.x-c.w/2" :y="Math.min(c.yo,c.yc)" :width="c.w" :height="Math.max(1,Math.abs(c.yc-c.yo))" :class="c.up?'c-up':'c-down'"/><rect :x="c.x-c.w/2" :y="355-c.volumeHeight" :width="c.w" :height="c.volumeHeight" :class="c.up?'v-up':'v-down'"/></g>
            <polyline v-if="chart.ma20" :points="chart.ma20" class="ma ma20"/><polyline v-if="chart.ma60" :points="chart.ma60" class="ma ma60"/>
          </svg>
          <div class="chart-foot"><span>{{ chart.first }}</span><span><i class="legend ma20-dot"></i>MA20 <i class="legend ma60-dot"></i>MA60</span><span>{{ chart.last }}</span></div>
          <small class="scope-note">{{ stockDetail.dataScope }}。当前涨幅不是“上市以来涨幅”。</small>
        </template>
      </section>
      <section class="detail-grid financial-grid">
        <article class="panel-q"><span>FINANCIAL SNAPSHOT</span><h3>最新财务指标</h3><div v-if="latestFinancial" class="metric-grid"><p><span>营业收入</span><b>{{ compactMoney(latestFinancial.revenue) }}</b><small :class="latestFinancial.revenueGrowth>=0?'up':'down'">同比 {{ metric(latestFinancial.revenueGrowth,'%') }}</small></p><p><span>归母净利润</span><b>{{ compactMoney(latestFinancial.profit) }}</b><small :class="latestFinancial.profitGrowth>=0?'up':'down'">同比 {{ metric(latestFinancial.profitGrowth,'%') }}</small></p><p><span>ROE</span><b>{{ metric(latestFinancial.roe,'%') }}</b><small>净资产收益率</small></p><p><span>毛利率</span><b>{{ metric(latestFinancial.grossMargin,'%') }}</b><small>销售毛利率</small></p><p><span>每股收益</span><b>{{ metric(latestFinancial.eps) }}</b><small>EPS</small></p><p><span>每股经营现金流</span><b>{{ metric(latestFinancial.cashflowPerShare) }}</b><small>现金质量参考</small></p></div><div v-else class="detail-state">{{ detailLoading?'正在读取财务数据…':'当前数据源暂无可用财务指标' }}</div><footer v-if="latestFinancial">报告期 {{ latestFinancial.reportDate }} · 披露日 {{ latestFinancial.publishDate }}</footer></article>
        <article class="panel-q"><span>RISK & TRADING</span><h3>行情统计</h3><div class="metric-grid stats" v-if="stockDetail"><p><span>区间最高</span><b>¥{{ metric(stockDetail.stats.high) }}</b></p><p><span>区间最低</span><b>¥{{ metric(stockDetail.stats.low) }}</b></p><p><span>有效交易日</span><b>{{ stockDetail.stats.tradingDays }}</b></p><p><span>近20日平均成交额</span><b>{{ compactMoney(stockDetail.stats.averageAmount20) }}</b></p></div><div v-else class="detail-state">等待本地行情数据</div><p class="notice">完整公司简介、准确上市日期、发行价及上市以来总回报将在补齐公司档案和全历史复权数据后开放。</p></article>
      </section>
      <section class="detail-grid">
        <article class="panel-q evidence"><span>INVESTMENT CASE</span><h3>结论与反证</h3><div class="positive"><i>+</i><p><b>核心理由</b>{{ selectedStock.reason }}</p></div><div class="negative"><i>!</i><p><b>可能推翻结论</b>{{ selectedStock.counter }}</p></div><footer>财报截止 {{ selectedStock.reportDate }} · 请结合最新公告复核</footer></article>
        <article class="panel-q dimensions"><span>FACTOR SCORE</span><h3>六维得分</h3><div v-for="d in [{n:'财务质量',v:selectedStock.quality,m:25},{n:'成长能力',v:selectedStock.growth,m:20},{n:'估值水平',v:selectedStock.valuation,m:20},{n:'中期趋势',v:selectedStock.trend,m:15},{n:'风险稳定',v:selectedStock.risk,m:10},{n:'流动性',v:selectedStock.liquidity,m:10}]" :key="d.n"><label>{{ d.n }}<b>{{ d.v }}/{{ d.m }}</b></label><p><i :style="{width:`${d.v/d.m*100}%`}"></i></p></div></article>
      </section>
      <section class="detail-grid lower">
        <article class="panel-q budget"><span>POSITION CALCULATOR</span><h3>预算换算</h3><label>本次可用预算 <span><b>¥</b><input type="number" min="0" step="1000" v-model.number="budget"></span></label><div class="budget-results"><p><span>建议仓位</span><b>{{ selectedStock.position[1] ? `${selectedStock.position[0]}–${selectedStock.position[1]}%` : '不建议' }}</b></p><p><span>按区间中值估算</span><b>{{ quantity }} 股</b></p><p><span>预计占用</span><b>{{ money(invested) }}</b></p></div><small>仅按本次预算与 100 股整数单位换算，不代表完整资产配置建议。</small></article>
        <article class="panel-q valuation"><span>VALUATION SNAPSHOT</span><h3>估值快照</h3><div><p><span>PE (TTM)</span><b>{{ selectedStock.pe ?? '—' }}</b><small>市盈率</small></p><p><span>PB</span><b>{{ selectedStock.pb ?? '—' }}</b><small>市净率</small></p><p><span>置信度</span><b>{{ selectedStock.confidence }}%</b><small>数据完整性</small></p></div><p class="notice">估值低不等于风险低，需要与质量和成长同时判断。</p></article>
      </section>
    </template>

    <template v-else-if="tab==='portfolio'">
      <section class="section-head"><div><span>MANUAL PORTFOLIO</span><h2>我的持仓</h2></div><p>仅保存在当前浏览器，不连接券商。</p></section>
      <form class="holding-form" @submit.prevent="addHolding"><input v-model="form.code" placeholder="股票代码" required><input v-model="form.name" placeholder="名称（可选）"><input type="number" step=".01" min=".01" v-model="form.cost" placeholder="持仓成本" required><input type="number" step="100" min="100" v-model="form.shares" placeholder="股数" required><button>添加持仓</button></form>
      <section class="portfolio-summary"><div><span>持仓估值</span><b>{{ money(totalValue) }}</b></div><div><span>持仓数量</span><b>{{ holdings.length }}</b></div><div><span>集中度提示</span><b>{{ holdings.length && holdings.length<10 ? '偏高' : '待评估' }}</b></div></section>
      <section class="stock-table"><div class="s-row p-row s-head"><span>标的</span><span>成本 / 现价</span><span>数量</span><span>市值</span><span>浮动盈亏</span><span></span></div><div class="s-row p-row" v-for="(h,i) in portfolio" :key="`${h.code}-${i}`"><span><b>{{ h.name }}</b><small>{{ h.code }} · 模型分 {{ h.score??'—' }}</small></span><span><b>¥{{ h.cost.toFixed(2) }} / ¥{{ h.price.toFixed(2) }}</b></span><span><b>{{ h.shares }} 股</b></span><span><b>{{ money(h.value) }}</b></span><span><b :class="h.pnl>=0?'up':'down'">{{ money(h.pnl) }}</b></span><span><button class="remove" @click="removeHolding(i)">移除</button></span></div><div v-if="!holdings.length" class="empty-q">还没有手工持仓，添加后可查看集中度与评级变化。</div></section>
    </template>

    <template v-else>
      <section class="section-head"><div><span>AUDITABLE MODEL</span><h2>模型验证与数据</h2></div><p>回测结果不代表未来表现。</p></section>
      <section class="validation-grid"><article v-for="m in [{n:'年化收益',v:`${data.validation.annualReturn}%`},{n:'最大回撤',v:`${data.validation.maxDrawdown}%`},{n:'正收益窗口',v:`${data.validation.winRate}%`},{n:'年化超额',v:`${data.validation.excessReturn}%`}]" :key="m.n"><span>{{ m.n }}</span><b>{{ m.v }}</b><small>{{ data.validation.period }}</small></article></section>
      <section class="source-grid"><article v-for="s in data.sources" :key="s.name"><i :class="s.state"></i><div><b>{{ s.name }}</b><span>{{ s.detail }}</span></div><em>{{ s.state==='ready'?'正常':'需要连接' }}</em></article></section>
      <div class="disclaimer"><b>重要提示</b><p>本页是研究与决策辅助工具，不构成证券投资建议。免费数据可能延迟、缺失或因上游变更而中断；实际决策前请复核上市公司公告与券商数据。</p></div>
    </template>
  </div>
  <div v-else class="q-loading"><span></span><p>正在读取量化分析…</p></div>
</template>

<style scoped>
.quant-page{max-width:1320px;margin:auto;padding:32px 28px 90px}.demo-banner{display:flex;align-items:center;gap:10px;background:#fff1d2;border:1px solid #edcf88;border-radius:12px;padding:10px 14px;color:#72521a;font-size:12px}.demo-banner b{background:#8b651d;color:white;padding:3px 7px;border-radius:5px}.demo-banner button{margin-left:auto;border:0;background:none;text-decoration:underline;cursor:pointer}.q-hero{display:flex;justify-content:space-between;align-items:flex-end;gap:36px;padding:46px 0 30px}.q-hero h1{font:clamp(42px,6vw,76px)/1 Georgia,"Songti SC";letter-spacing:-3px;margin:10px 0 15px;max-width:760px}.q-hero>div>p:last-child{color:var(--muted);line-height:1.7}.as-of{min-width:250px;background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:15px;display:grid;grid-template-columns:10px 1fr;gap:10px;align-items:center}.as-of>span{width:9px;height:9px;border-radius:50%;background:#4eb66c}.as-of>span.demo{background:#e2a62b}.as-of small,.as-of b{display:block}.as-of small{font-size:10px;color:var(--muted)}.as-of b{font-size:12px;margin-top:3px}.as-of em{grid-column:2;font:10px monospace;color:var(--muted);font-style:normal}.q-tabs{display:flex;border-bottom:1px solid var(--line);margin-bottom:24px}.q-tabs button{border:0;background:none;padding:13px 17px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent}.q-tabs button.active{color:var(--green);border-color:var(--green);font-weight:700}.market-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.market-grid article,.panel-q,.validation-grid article{background:var(--paper);border:1px solid var(--line);border-radius:17px;padding:20px}.market-grid span{display:block;color:var(--muted);font-size:11px}.market-grid b{font:27px Georgia;display:block;margin:13px 0 5px}.market-grid em{font-style:normal;font-size:12px}.up{color:#d44e43!important}.down{color:#168260!important}.breadth div{height:5px;background:#e9e9e1;border-radius:6px;margin:8px 0;overflow:hidden}.breadth i{display:block;height:100%;background:var(--green)}.breadth small{font-size:10px;color:var(--muted)}.section-head{display:flex;justify-content:space-between;align-items:end;padding:42px 0 17px}.section-head span,.panel-q>span{font:700 10px monospace;letter-spacing:1.4px;color:var(--green)}.section-head h2{font:35px Georgia,"Songti SC";margin:6px 0}.section-head p{color:var(--muted);font-size:12px}.filters{display:flex;gap:10px;background:#e8e8df;border-radius:13px;padding:8px;margin-bottom:12px}.filters>input,.filters select{border:0;background:var(--paper);border-radius:9px;padding:10px 12px}.filters>input{min-width:240px}.filters label{margin-left:auto;display:flex;align-items:center;gap:8px;font-size:11px;color:var(--muted);padding:0 8px}.stock-table{background:var(--paper);border:1px solid var(--line);border-radius:17px;overflow:hidden}.s-row{display:grid;grid-template-columns:1.1fr .9fr .65fr 2.4fr .7fr .65fr;gap:13px;align-items:center;padding:15px 18px;border-top:1px solid #e8e8e1;font-size:12px}.s-row:first-child{border-top:0}.s-row b,.s-row small{display:block}.s-row small{font-size:9px;color:var(--muted);margin-top:5px;line-height:1.4}.s-row>span:nth-child(4)>b{font-weight:500;line-height:1.55}.s-head{background:#f5f4ee;color:var(--muted);font-size:9px;padding-top:10px;padding-bottom:10px}.s-row button{border:1px solid var(--line);background:white;border-radius:8px;padding:7px 9px;cursor:pointer;font-size:10px}.score{display:inline-grid!important;place-content:center;width:37px;height:30px;border-radius:8px;font:700 15px Georgia}.strong{background:#174f42!important;color:#c8f560!important}.good{background:#dff0cb!important;color:#285d31!important}.neutral{background:#e8e6d8!important;color:#5e5c4e!important}.warn{background:#ffe1b8!important;color:#815617!important}.avoid{background:#f4d4d0!important;color:#8c3029!important}.flags{color:#b14a34!important}.empty-q{text-align:center;padding:50px;color:var(--muted)}.detail-hero{display:flex;align-items:center;gap:26px;background:var(--green);color:white;border-radius:22px;padding:28px 32px;margin-top:8px}.detail-hero>div:first-child{margin-right:auto}.detail-hero span{font-size:10px;color:#b9cec7}.detail-hero h2{font:40px Georgia,"Songti SC";margin:6px 0}.detail-hero p{margin:0;color:#d6e1dd}.hero-price{text-align:right}.hero-price b{display:block;font:28px Georgia}.hero-price em{font-style:normal}.big-score{width:100px;height:82px;border-radius:14px;display:grid;place-content:center;text-align:center}.big-score b{font:38px Georgia;line-height:1}.big-score span{font-size:9px}.detail-grid{display:grid;grid-template-columns:1.25fr .75fr;gap:14px;margin-top:14px}.panel-q h3{font:25px Georgia,"Songti SC";margin:6px 0 20px}.positive,.negative{display:flex;gap:12px;border-radius:12px;padding:14px;margin:10px 0}.positive{background:#e7f2df}.negative{background:#fff0dc}.positive i,.negative i{width:24px;height:24px;display:grid;place-content:center;border-radius:50%;font-style:normal;font-weight:bold;background:white}.evidence p{margin:0;line-height:1.65;font-size:12px}.evidence p b{display:block;margin-bottom:4px}.evidence footer{color:var(--muted);font-size:10px;margin-top:17px}.dimensions>div{margin:11px 0}.dimensions label{display:flex;justify-content:space-between;font-size:10px}.dimensions p{height:6px;background:#e9e9e1;border-radius:6px;overflow:hidden;margin:5px 0}.dimensions p i{display:block;height:100%;background:var(--green)}.lower{grid-template-columns:1fr 1fr}.budget>label{display:block;font-size:11px;color:var(--muted)}.budget>label>span{display:flex;align-items:center;border:1px solid var(--line);border-radius:10px;margin-top:7px;background:white}.budget>label b{padding-left:12px}.budget input{border:0;padding:12px;width:100%;outline:0}.budget-results{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:15px 0}.budget-results p,.valuation>div p{background:#f2f1e9;border-radius:10px;padding:12px;margin:0}.budget-results span,.valuation p span{display:block;font-size:9px;color:var(--muted)}.budget-results b,.valuation p b{display:block;font:21px Georgia;margin-top:7px}.budget>small{color:var(--muted);font-size:9px}.valuation>div{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.valuation small{font-size:9px;color:var(--muted)}.valuation .notice{font-size:10px;color:var(--muted);margin:18px 0 0}.holding-form{display:grid;grid-template-columns:1fr 1.3fr 1fr 1fr auto;gap:8px;background:#e8e8df;padding:9px;border-radius:13px}.holding-form input{border:0;border-radius:8px;padding:11px}.holding-form button{border:0;background:var(--green);color:white;border-radius:8px;padding:0 18px}.portfolio-summary{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:12px 0}.portfolio-summary div{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:18px}.portfolio-summary span{display:block;color:var(--muted);font-size:10px}.portfolio-summary b{display:block;font:24px Georgia;margin-top:8px}.p-row{grid-template-columns:1.2fr 1fr .7fr 1fr 1fr .5fr}.remove{color:#a43d35}.validation-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.validation-grid span,.validation-grid small{display:block;color:var(--muted);font-size:10px}.validation-grid b{display:block;font:30px Georgia;margin:15px 0 8px}.source-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:14px 0}.source-grid article{display:flex;align-items:center;gap:11px;background:var(--paper);border:1px solid var(--line);border-radius:13px;padding:16px}.source-grid i{width:9px;height:9px;background:#d2a039;border-radius:50%}.source-grid i.ready{background:#54a66b}.source-grid b,.source-grid span{display:block}.source-grid span{font-size:9px;color:var(--muted);margin-top:3px}.source-grid em{margin-left:auto;font-style:normal;font-size:9px}.disclaimer{border:1px solid #e4c98f;background:#fff6e3;border-radius:13px;padding:18px;color:#72521a}.disclaimer p{font-size:11px;line-height:1.7;margin:6px 0 0}.q-loading{height:calc(100vh - 74px);display:grid;place-content:center;text-align:center;color:var(--muted)}
.top-head{padding-top:18px}.experimental-note{display:flex;gap:12px;align-items:center;background:#fff3d9;border:1px solid #ecd18c;border-radius:12px;padding:12px 15px;color:#72521a;font-size:10px;margin-bottom:14px}.experimental-note b{white-space:nowrap}.recommendation-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.recommendation-card{background:var(--paper);border:1px solid var(--line);border-radius:17px;padding:18px}.recommendation-card header{display:flex;align-items:center;gap:11px}.recommendation-card header i{display:grid;place-content:center;width:42px;height:42px;border-radius:12px;background:var(--green);color:#c8f560;font:700 15px Georgia;font-style:normal}.recommendation-card header div{margin-right:auto}.recommendation-card header b,.recommendation-card header span{display:block}.recommendation-card header span{font-size:9px;color:var(--muted);margin-top:4px}.recommendation-card header em{font-size:9px;color:var(--muted);font-style:normal}.recommendation-card header strong{display:grid;place-content:center;width:42px;height:34px;border-radius:9px;font:700 16px Georgia}.recommendation-card>p{font-size:12px;line-height:1.65;margin:16px 0 10px}.recommendation-card ul{padding-left:17px;margin:0 0 13px}.recommendation-card li{font-size:10px;color:#4b625b;line-height:1.7}.rec-risk{background:#fff0dc;border-radius:9px;padding:10px}.rec-risk b,.rec-risk span{display:block;font-size:9px}.rec-risk span{margin-top:4px;color:#775c3e;line-height:1.5}.recommendation-card footer{display:flex;align-items:center;gap:12px;margin-top:13px;font-size:9px;color:var(--muted)}.recommendation-card footer button{margin-left:auto;border:1px solid var(--line);background:white;border-radius:8px;padding:7px 9px;cursor:pointer;font-size:9px}
.profile-strip{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;margin:14px 0;background:var(--line);border:1px solid var(--line);border-radius:15px;overflow:hidden}.profile-strip div{background:var(--paper);padding:14px 17px}.profile-strip span,.metric-grid span{display:block;color:var(--muted);font-size:9px}.profile-strip b{display:block;margin-top:6px;font-size:12px}.chart-panel{margin-top:14px}.chart-head{display:flex;justify-content:space-between;align-items:start}.chart-head h3{margin-bottom:4px}.range-buttons{display:flex;background:#eeede6;border-radius:9px;padding:3px}.range-buttons button{border:0;background:transparent;padding:7px 10px;border-radius:7px;font-size:10px;cursor:pointer}.range-buttons button.active{background:white;color:var(--green);font-weight:700}.chart-summary{display:flex;gap:25px;margin:15px 0 8px;font-size:10px;color:var(--muted)}.chart-summary b{display:block;margin-top:4px;font-size:13px;color:#333}.stock-chart{width:100%;height:370px;display:block}.grid-line{stroke:#e7e6df;stroke-width:1}.c-up{fill:#d55349;stroke:#d55349}.c-down{fill:#168260;stroke:#168260}.v-up{fill:#edbbb5}.v-down{fill:#a9d0c5}.ma{fill:none;stroke-width:1.5;vector-effect:non-scaling-stroke}.ma20{stroke:#d29c31}.ma60{stroke:#5676b8}.chart-foot{display:flex;justify-content:space-between;color:var(--muted);font-size:9px}.legend{display:inline-block;width:12px;height:2px;vertical-align:middle;margin:0 4px 2px 10px}.ma20-dot{background:#d29c31}.ma60-dot{background:#5676b8}.scope-note{display:block;margin-top:12px;color:var(--muted);font-size:9px}.detail-state{padding:55px 20px;text-align:center;color:var(--muted);background:#f3f2eb;border-radius:12px;font-size:11px}.detail-state.warning{color:#7b581d;background:#fff3d9}.financial-grid{grid-template-columns:1fr 1fr}.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.metric-grid p{margin:0;background:#f2f1e9;border-radius:10px;padding:12px}.metric-grid b{display:block;font:19px Georgia;margin:7px 0 4px}.metric-grid small{font-size:9px;color:var(--muted)}.metric-grid.stats{grid-template-columns:1fr 1fr}.financial-grid footer{margin-top:14px;color:var(--muted);font-size:9px}.financial-grid .notice{color:var(--muted);font-size:10px;line-height:1.6;margin-top:16px}
@media(max-width:900px){.quant-page{padding:22px 16px 60px}.q-hero{align-items:start;flex-direction:column}.as-of{width:100%}.q-tabs{overflow-x:auto}.q-tabs button{white-space:nowrap}.market-grid{grid-template-columns:1fr 1fr}.section-head{align-items:start;flex-direction:column}.filters{flex-wrap:wrap}.filters>input{min-width:0;flex:1}.filters label{width:100%;margin:0}.stock-table{overflow-x:auto}.s-row{min-width:980px}.detail-grid,.lower,.financial-grid,.recommendation-grid{grid-template-columns:1fr}.profile-strip{grid-template-columns:1fr 1fr}.holding-form{grid-template-columns:1fr 1fr}.holding-form button{min-height:42px}.validation-grid{grid-template-columns:1fr 1fr}.source-grid{grid-template-columns:1fr}.stock-chart{height:300px}.chart-summary{flex-wrap:wrap}}
@media(max-width:520px){.market-grid,.portfolio-summary,.validation-grid,.profile-strip{grid-template-columns:1fr}.q-hero h1{font-size:44px}.detail-hero{align-items:flex-start;flex-wrap:wrap}.big-score{width:80px}.budget-results,.valuation>div,.metric-grid{grid-template-columns:1fr}.holding-form{grid-template-columns:1fr}.chart-head{display:block}.range-buttons{margin-top:12px}.stock-chart{height:245px}}
</style>
