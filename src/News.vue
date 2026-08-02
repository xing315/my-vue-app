<script>
import { supabase } from './supabase.js'

export default {
  emits:['back'],
  data(){return{
    tab:'全部',query:'',saved:[],news:[],newsLoading:true,newsError:'',newsSource:'',fetchedAt:null,
    market:null,tickers:[],marketError:'',
    aiQuestion:'',aiLoading:false,aiError:'',messages:[],quotaRemaining:null,
    suggestions:['解释今天市场宽度代表什么','如何判断一家公司估值是否合理？','帮我解释市盈率和市净率']
  }},
  computed:{
    tabs(){return ['全部',...new Set(this.news.map(n=>n.category))]},
    filtered(){const q=this.query.trim().toLowerCase();return this.news.filter(n=>(this.tab==='全部'||n.category===this.tab)&&(!q||`${n.title} ${n.summary}`.toLowerCase().includes(q)))},
    breadth(){return Number(this.market?.breadth??0)},
    sentiment(){if(!this.market)return '数据不足';return this.breadth>=60?'偏强':this.breadth>=45?'中性':'偏弱'}
  },
  mounted(){this.refresh()},
  methods:{
    async refresh(){await Promise.allSettled([this.loadNews(),this.loadMarket()])},
    async loadNews(){
      this.newsLoading=true;this.newsError=''
      try{
        let payload
        try{const response=await fetch('/api/quant/news',{cache:'no-store',signal:AbortSignal.timeout(5000)});if(!response.ok)throw new Error(`本地新闻 HTTP ${response.status}`);payload=await response.json();if(payload.mode!=='live')throw new Error('非实时数据')}
        catch{
          try{const response=await fetch('/.netlify/functions/financial-news',{cache:'no-store'});if(!response.ok)throw new Error(`Netlify 新闻 HTTP ${response.status}`);payload=await response.json()}
          catch{
            const {data,error}=await supabase.functions.invoke('financial-news',{body:{refresh:true}})
            if(error)throw error
            payload=data
          }
        }
        if(!payload?.items?.length)throw new Error('新闻源没有返回有效内容')
        this.news=payload.items;this.newsSource=payload.source;this.fetchedAt=payload.fetchedAt
      }catch(error){this.news=[];this.newsError=`${error.message||'实时新闻暂时无法获取'}。页面不会展示演示新闻，请稍后重试。`}
      finally{this.newsLoading=false}
    },
    async loadMarket(){
      this.marketError=''
      try{
        const {data:snapshots,error:snapshotError}=await supabase.from('quant_market_snapshots').select('trade_date,updated_at,coverage_count,eligible_count,market').order('trade_date',{ascending:false}).limit(1)
        if(snapshotError)throw snapshotError
        if(!snapshots?.[0])throw new Error('暂无量化市场快照')
        const {data:rows,error:scoreError}=await supabase.from('quant_latest_scores').select('symbol,name,price,change_percent,score').eq('excluded',false).order('score',{ascending:false}).limit(4)
        if(scoreError)throw scoreError
        this.market={...snapshots[0].market,tradeDate:snapshots[0].trade_date,updatedAt:snapshots[0].updated_at,coverage:snapshots[0].coverage_count,eligible:snapshots[0].eligible_count}
        this.tickers=(rows||[]).map(row=>({code:row.symbol,name:row.name,price:Number(row.price),change:Number(row.change_percent),score:row.score}))
      }catch(error){this.market=null;this.tickers=[];this.marketError=error.message||'市场快照暂时不可用'}
    },
    formatTime(value){if(!value)return '时间未知';const date=new Date(value);return Number.isNaN(date.getTime())?String(value):date.toLocaleString('zh-CN',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})},
    toggle(id){this.saved.includes(id)?this.saved=this.saved.filter(x=>x!==id):this.saved.push(id)},
    openNews(item){if(item.url)window.open(item.url,'_blank','noopener,noreferrer')},
    useSuggestion(text){this.aiQuestion=text;this.askDeepSeek()},
    async askDeepSeek(){
      const question=this.aiQuestion.trim();if(!question||this.aiLoading)return
      this.aiError='';const {data:{session}}=await supabase.auth.getSession()
      if(!session){this.aiError='为了保护 API 额度，AI 问答仅对登录用户开放。请先点击右上角登录。';return}
      this.messages.push({role:'user',content:question});this.aiQuestion='';this.aiLoading=true
      try{
        const history=this.messages.slice(-8).map(({role,content})=>({role,content}))
        const {data,error}=await supabase.functions.invoke('deepseek-chat',{body:{messages:history}})
        if(error){if(data?.code==='DAILY_LIMIT'){this.quotaRemaining=0;throw new Error('今天的 10 次 AI 对话额度已用完，请明天再试。')}throw error}
        if(!data?.answer)throw new Error('AI 暂未返回有效内容')
        this.quotaRemaining=data.remaining;this.messages.push({role:'assistant',content:data.answer,usage:data.usage})
      }catch(error){this.aiError=error?.message?.includes('10 次')?error.message:error?.message?.includes('non-2xx')?'AI 服务尚未完成配置，或当前额度不足。':(error?.message||'AI 服务暂时不可用，请稍后再试。')}
      finally{this.aiLoading=false}
    }
  }
}
</script>

<template><div class="page-wrap news-page">
 <button class="back-button" @click="$emit('back')" aria-label="返回上一级">← <span>返回上一级</span></button>
 <div class="news-hero"><div><p class="eyebrow">LIVE FINANCIAL SIGNAL</p><h1 class="page-title">真实财经资讯</h1><p class="page-lead">新闻在每次进入页面时实时获取；行情与评分来自已发布的量化快照，不使用演示数字。</p></div><div class="market" :class="{unavailable:!market}"><small>全市场上涨宽度</small><strong>{{market?`${breadth}%`:'—'}}</strong><span>{{sentiment}}</span></div></div>
 <section class="data-status"><div><i :class="newsError?'error':'ready'"></i><span><b>财经新闻</b><small>{{newsError||`${newsSource||'正在连接'} · 获取于 ${formatTime(fetchedAt)}`}}</small></span></div><div><i :class="marketError?'error':'ready'"></i><span><b>量化市场快照</b><small>{{marketError||(market?`${market.tradeDate} · 覆盖 ${market.coverage} 只`:'正在读取真实快照…')}}</small></span></div><button @click="refresh" :disabled="newsLoading">{{newsLoading?'刷新中…':'刷新真实数据'}}</button></section>
 <section class="ai-studio">
  <div class="ai-intro"><div><span class="ai-badge">OWNER ONLY</span><h2>专属财经与知识助手</h2><p>AI 不会自动知道实时新闻；如需讨论当日事件，请把下方真实新闻标题或内容粘贴到问题中。</p></div><div class="ai-orb">DS</div></div>
  <div v-if="!messages.length" class="suggestions"><button v-for="s in suggestions" :key="s" @click="useSuggestion(s)">{{s}} <span>↗</span></button></div>
  <div v-else class="conversation"><article v-for="(m,i) in messages" :key="i" :class="['message',m.role]"><div class="message-role">{{m.role==='user'?'你':'DeepSeek'}}</div><p>{{m.content}}</p></article><div v-if="aiLoading" class="thinking"><i></i><i></i><i></i><span>正在组织答案…</span></div></div>
  <form class="ai-input" @submit.prevent="askDeepSeek"><textarea v-model="aiQuestion" @keydown.enter.exact.prevent="askDeepSeek" rows="2" placeholder="向 DeepSeek 提问；涉及实时事件时请附上新闻内容"></textarea><button :disabled="aiLoading||!aiQuestion.trim()">{{aiLoading?'…':'↑'}}</button></form>
  <div v-if="quotaRemaining!==null" class="quota-info">今日剩余 {{quotaRemaining}} / 10 次</div><div v-if="aiError" class="ai-error">{{aiError}}</div>
 </section>
 <div v-if="tickers.length" class="ticker"><span v-for="t in tickers" :key="t.code">{{t.name}} <b>¥{{t.price.toFixed(2)}}</b> <i :class="t.change>=0?'positive':'negative'">{{t.change>=0?'+':''}}{{t.change.toFixed(2)}}%</i><small>模型 {{t.score}}</small></span></div>
 <div class="search"><span>⌕</span><input v-model="query" placeholder="搜索真实新闻标题或摘要"><kbd>实时快讯</kbd></div>
 <div class="filters"><button v-for="t in tabs" :key="t" :class="['pill',{active:tab===t}]" @click="tab=t">{{t}}</button></div>
 <div v-if="newsLoading" class="news-state">正在获取真实财经新闻…</div>
 <div v-else-if="newsError" class="news-state error"><b>新闻暂时不可用</b><p>{{newsError}}</p><button @click="loadNews">重新获取</button></div>
 <div v-else class="news-layout"><section><article v-for="(n,i) in filtered" :key="n.id"><div class="rank">{{String(i+1).padStart(2,'0')}}</div><div class="news-body" @click="openNews(n)"><div class="meta"><b>{{n.category}}</b>{{n.source}} · {{formatTime(n.publishedAt)}}</div><h2>{{n.title}}</h2><p v-if="n.summary">{{n.summary}}</p><a v-if="n.url" :href="n.url" target="_blank" rel="noopener noreferrer" @click.stop>查看原文 ↗</a></div><button @click="toggle(n.id)" :class="{saved:saved.includes(n.id)}">{{saved.includes(n.id)?'★':'☆'}}</button></article><div v-if="!filtered.length" class="news-state">没有匹配的实时新闻</div></section><aside><p class="eyebrow">DATA PROVENANCE</p><h3>数据来源</h3><p>新闻：{{newsSource}}</p><p>行情：Supabase 量化盘后快照</p><p>数据截止：{{formatTime(market?.updatedAt)}}</p><hr><small>已收藏 {{saved.length}} 条 · 原文归新闻发布方所有</small></aside></div>
</div></template>

<style scoped>
.back-button{border:0;background:none;color:var(--green);cursor:pointer;padding:0 0 20px;font-size:13px}.back-button span{margin-left:5px}.news-hero{display:flex;justify-content:space-between;align-items:end}.market{width:158px;height:158px;border-radius:50%;border:12px solid #dce8c4;display:grid;place-content:center;text-align:center;flex:none}.market.unavailable{border-color:#ddd}.market strong{font:38px Georgia;color:var(--green);margin:5px 0}.market span,.market small{font-size:10px;color:var(--green)}.data-status{display:flex;align-items:center;gap:24px;background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:13px 15px;margin:28px 0}.data-status>div{display:flex;align-items:center;gap:9px}.data-status i{width:8px;height:8px;border-radius:50%;background:#55ad69}.data-status i.error{background:#d75b4d}.data-status b,.data-status small{display:block}.data-status b{font-size:11px}.data-status small{color:var(--muted);font-size:9px;margin-top:3px}.data-status button{margin-left:auto;border:1px solid var(--line);background:white;border-radius:8px;padding:8px 11px;font-size:10px;cursor:pointer}.ticker{margin:28px 0 18px;background:var(--ink);color:white;padding:16px 20px;border-radius:12px;display:flex;justify-content:space-between;gap:20px;overflow:auto;white-space:nowrap;font-size:11px}.ticker b{margin:0 5px}.ticker i{font-style:normal}.ticker .positive{color:#ff9382}.ticker .negative{color:#75d4b7}.ticker small{margin-left:7px;color:#aebdb8}.search{display:flex;align-items:center;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:0 16px}.search input{flex:1;border:0;background:none;padding:16px;outline:none}.search kbd{font-size:11px;color:var(--green)}.filters{display:flex;gap:8px;margin:18px 0 28px;overflow:auto}.news-layout{display:grid;grid-template-columns:1fr 300px;gap:24px}.news-layout section{border-top:1px solid var(--line)}.news-layout article{display:grid;grid-template-columns:48px 1fr 34px;gap:16px;padding:22px 0;border-bottom:1px solid var(--line);align-items:start}.rank{font:20px Georgia;color:#a4aaa2}.meta{font-size:10px;color:var(--muted)}.meta b{color:var(--green);margin-right:9px}.news-body{cursor:pointer}.news-body h2{font:21px/1.45 Georgia,"Songti SC";margin:7px 0}.news-body>p{font-size:11px;line-height:1.65;color:var(--muted);margin:7px 0}.news-body a{font-size:10px;color:var(--green)}.news-layout article>button{border:0;background:none;font-size:24px;cursor:pointer;color:#9ca39f}.saved{color:#e4a72e!important}aside{background:#dfe9c8;border-radius:18px;padding:28px;height:max-content}aside h3{font:27px Georgia;margin:10px 0}aside p{color:#59645f;line-height:1.7;font-size:11px}aside hr{border:0;border-top:1px solid #bfcab0;margin:24px 0}.news-state{text-align:center;padding:55px;background:var(--paper);border:1px solid var(--line);border-radius:15px;color:var(--muted)}.news-state.error{color:#7a4237}.news-state button{border:0;background:var(--green);color:white;border-radius:8px;padding:9px 13px}
.ai-studio{margin:24px 0;background:var(--ink);color:white;border-radius:24px;padding:30px}.ai-intro{display:flex;align-items:center;justify-content:space-between}.ai-badge{display:inline-block;background:var(--lime);color:var(--green);font-size:10px;font-weight:900;letter-spacing:1.5px;padding:6px 9px;border-radius:999px}.ai-intro h2{font:30px Georgia,"Songti SC";margin:14px 0 8px}.ai-intro p{margin:0;color:#aebdb8;font-size:12px}.ai-orb{width:58px;height:58px;border:1px solid #52736a;border-radius:50%;display:grid;place-items:center;color:var(--lime);font:20px Georgia}.suggestions{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:28px}.suggestions button{border:1px solid #3d554e;background:#22302c;color:#dce5e2;border-radius:12px;padding:14px;text-align:left;cursor:pointer;font-size:12px;display:flex;justify-content:space-between}.conversation{max-height:420px;overflow:auto;margin-top:25px}.message{border:0;padding:0;margin:0 0 18px}.message-role{font-size:10px;letter-spacing:1.4px;color:var(--lime);margin-bottom:7px}.message p{white-space:pre-wrap;line-height:1.75;margin:0;background:#23332e;border-radius:5px 16px 16px 16px;padding:15px}.message.user{text-align:right}.message.user p{display:inline-block;background:#dfe9c8;color:var(--ink);text-align:left}.thinking{display:flex;gap:5px;align-items:center;color:#aebdb8;font-size:12px}.thinking i{width:6px;height:6px;background:var(--lime);border-radius:50%}.ai-input{display:flex;align-items:center;margin-top:22px;background:#f7f4ed;border-radius:16px;padding:8px}.ai-input textarea{flex:1;border:0;background:transparent;resize:none;outline:none;padding:10px 12px}.ai-input button{width:42px;height:42px;border:0;border-radius:50%;background:var(--green);color:var(--lime);font-size:20px}.ai-error{color:#ffb5a4;font-size:12px;margin-top:10px}.quota-info{color:#aebdb8;font-size:11px;text-align:right;margin-top:8px}
@media(max-width:780px){.market{display:none}.news-layout{grid-template-columns:1fr}.ticker{justify-content:flex-start}aside{order:-1}.data-status{align-items:flex-start;flex-direction:column}.data-status button{margin:0}.suggestions{grid-template-columns:1fr}}
</style>
