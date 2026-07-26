<script>
import { supabase } from './supabase.js'

export default{
 data(){return{
  tab:'全部',query:'',saved:[],
  aiQuestion:'',aiLoading:false,aiError:'',messages:[],quotaRemaining:null,
  suggestions:['分析一下 AI 行业未来三年的机会','普通人该如何理解利率变化？','帮我解释市盈率和市净率'],
  tabs:['全部','宏观','市场','科技','商业'],news:[
 {cat:'宏观',time:'09:30',title:'全球市场等待新一轮经济数据，风险偏好温和回升',source:'财经晨报',hot:96},
 {cat:'科技',time:'08:45',title:'人工智能应用加速落地，企业服务迎来新一轮升级',source:'科技前线',hot:91},
 {cat:'市场',time:'08:10',title:'主要指数震荡整理，新能源与消费板块表现活跃',source:'市场观察',hot:88},
 {cat:'商业',time:'昨天',title:'从产品到体验：新消费品牌正在重写增长逻辑',source:'商业评论',hot:82},
 {cat:'科技',time:'昨天',title:'端侧智能成为焦点，下一代个人设备会如何变化',source:'未来实验室',hot:79},
 {cat:'宏观',time:'07.25',title:'城市更新与服务消费释放长期发展新空间',source:'经济视野',hot:74}
 ]}},
 computed:{filtered(){return this.news.filter(n=>(this.tab==='全部'||n.cat===this.tab)&&n.title.includes(this.query))}},
 methods:{
  toggle(i){this.saved.includes(i)?this.saved=this.saved.filter(x=>x!==i):this.saved.push(i)},
  useSuggestion(text){this.aiQuestion=text;this.askDeepSeek()},
  async askDeepSeek(){
   const question=this.aiQuestion.trim()
   if(!question||this.aiLoading)return
   this.aiError=''
   const {data:{session}}=await supabase.auth.getSession()
   if(!session){
    this.aiError='为了保护 API 额度，AI 问答仅对登录用户开放。请先点击右上角登录。'
    return
   }
   const userMessage={role:'user',content:question}
   this.messages.push(userMessage)
   this.aiQuestion=''
   this.aiLoading=true
   try{
    const history=this.messages.slice(-8).map(({role,content})=>({role,content}))
   const {data,error}=await supabase.functions.invoke('deepseek-chat',{body:{messages:history}})
    if(error){
     if(data?.code==='DAILY_LIMIT'){
      this.quotaRemaining=0
      throw new Error('今天的 10 次 AI 对话额度已用完，请明天再试。')
     }
     if(data?.code==='OWNER_ONLY'||data?.error?.includes('仅限网站所有者')){
      throw new Error('此 AI 功能仅限网站所有者账户使用。')
     }
     throw error
    }
    if(!data?.answer)throw new Error('AI 暂未返回有效内容')
    this.quotaRemaining=data.remaining
    this.messages.push({role:'assistant',content:data.answer,usage:data.usage})
   }catch(error){
    console.error('DeepSeek 调用失败',error)
    this.aiError=error?.message?.includes('10 次')
      ?error.message
      :error?.message?.includes('仅限网站所有者')
      ?error.message
      :error?.message?.includes('non-2xx')
      ?'AI 服务尚未完成配置，或当前额度不足。'
      :(error?.message||'AI 服务暂时不可用，请稍后再试。')
   }finally{this.aiLoading=false}
  }
 }
}
</script>
<template><div class="page-wrap news-page">
 <div class="news-hero"><div><p class="eyebrow">Daily Signal</p><h1 class="page-title">新闻财经脉搏</h1><p class="page-lead">少一点噪音，多一点信号。快速浏览值得关注的市场、科技与商业动态。</p></div><div class="market"><small>市场情绪</small><strong>72</strong><span>偏积极 ↑</span></div></div>
 <section class="ai-studio">
  <div class="ai-intro"><div><span class="ai-badge">OWNER ONLY</span><h2>专属财经与知识助手</h2><p>仅网站所有者账户可使用，每日限 10 次。AI 回答不等于实时新闻，也不构成投资建议。</p></div><div class="ai-orb">DS</div></div>
  <div v-if="!messages.length" class="suggestions"><button v-for="s in suggestions" @click="useSuggestion(s)">{{s}} <span>↗</span></button></div>
  <div v-else class="conversation">
   <article v-for="(m,i) in messages" :class="['message',m.role]">
    <div class="message-role">{{m.role==='user'?'你':'DeepSeek'}}</div>
    <p>{{m.content}}</p>
   </article>
   <div v-if="aiLoading" class="thinking"><i></i><i></i><i></i><span>正在思考并组织答案…</span></div>
  </div>
  <form class="ai-input" @submit.prevent="askDeepSeek">
   <textarea v-model="aiQuestion" @keydown.enter.exact.prevent="askDeepSeek" rows="2" placeholder="向 DeepSeek 提问，例如：降息通常会如何影响股票和黄金？"></textarea>
   <button :disabled="aiLoading||!aiQuestion.trim()" aria-label="发送问题">{{aiLoading?'…':'↑'}}</button>
  </form>
  <div v-if="quotaRemaining!==null" class="quota-info">今日剩余 {{quotaRemaining}} / 10 次</div>
  <div v-if="aiError" class="ai-error">{{aiError}}</div>
 </section>
 <div class="ticker"><span>上证指数 <b>3,428.16</b> <i>+0.42%</i></span><span>恒生指数 <b>24,388.13</b> <i>+0.73%</i></span><span>黄金 <b>2,386.40</b> <i>+0.18%</i></span><span>USD/CNY <b>7.1523</b> <em>-0.05%</em></span></div>
 <div class="search"><span>⌕</span><input v-model="query" placeholder="搜索新闻、行业或关键词"><kbd>实时简报</kbd></div>
 <div class="filters"><button v-for="t in tabs" :class="['pill',{active:tab===t}]" @click="tab=t">{{t}}</button></div>
 <div class="news-layout"><section><article v-for="(n,i) in filtered"><div class="rank">{{String(i+1).padStart(2,'0')}}</div><div><div class="meta"><b>{{n.cat}}</b> {{n.source}} · {{n.time}}</div><h2>{{n.title}}</h2><div class="heat"><span :style="{width:n.hot+'%'}"></span></div></div><button @click="toggle(i)" :class="{saved:saved.includes(i)}" :aria-label="saved.includes(i)?'取消收藏':'收藏'">{{saved.includes(i)?'★':'☆'}}</button></article></section><aside><p class="eyebrow">Editor's Pick</p><h3>今日值得关注</h3><div class="big-num">03</div><p>宏观数据、AI 应用落地与消费复苏，是今天最值得持续追踪的三条主线。</p><hr><small>已收藏 {{saved.length}} 条资讯</small></aside></div>
</div></template>
<style scoped>
.news-hero{display:flex;justify-content:space-between;align-items:end}.market{width:150px;height:150px;border-radius:50%;border:12px solid #dce8c4;display:grid;place-content:center;text-align:center}.market strong{font:44px Georgia;color:var(--green)}.market span{font-size:11px;color:var(--green)}.ticker{margin:40px 0 18px;background:var(--ink);color:white;padding:16px 20px;border-radius:12px;display:flex;justify-content:space-between;gap:20px;overflow:auto;white-space:nowrap;font-size:12px}.ticker b{margin:0 6px}.ticker i{color:var(--lime);font-style:normal}.ticker em{color:#ff9983;font-style:normal}.search{display:flex;align-items:center;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:0 16px}.search input{flex:1;border:0;background:none;padding:16px;outline:none}.search kbd{font-size:11px;color:var(--green)}.filters{display:flex;gap:8px;margin:18px 0 28px}.news-layout{display:grid;grid-template-columns:1fr 300px;gap:24px}.news-layout section{border-top:1px solid var(--line)}article{display:grid;grid-template-columns:48px 1fr 34px;gap:16px;padding:22px 0;border-bottom:1px solid var(--line);align-items:center}.rank{font:20px Georgia;color:#a4aaa2}.meta{font-size:11px;color:var(--muted)}.meta b{color:var(--green);margin-right:9px}h2{font:22px/1.4 Georgia,"Songti SC";margin:7px 0}.heat{width:100px;height:3px;background:#ddd}.heat span{display:block;height:100%;background:#ef7354}article button{border:0;background:none;font-size:24px;cursor:pointer;color:#9ca39f}.saved{color:#e4a72e!important}aside{background:#dfe9c8;border-radius:18px;padding:28px;height:max-content}aside h3{font:27px Georgia;margin:10px 0}.big-num{font:80px Georgia;color:var(--green);line-height:1}aside p:not(.eyebrow){color:#59645f;line-height:1.7}aside hr{border:0;border-top:1px solid #bfcab0;margin:24px 0}
.ai-studio{margin:42px 0 24px;background:var(--ink);color:white;border-radius:24px;padding:30px;box-shadow:0 20px 45px #10221b1c}.ai-intro{display:flex;align-items:center;justify-content:space-between}.ai-badge{display:inline-block;background:var(--lime);color:var(--green);font-size:10px;font-weight:900;letter-spacing:1.5px;padding:6px 9px;border-radius:999px}.ai-intro h2{font:30px Georgia,"Songti SC";margin:14px 0 8px}.ai-intro p{margin:0;color:#aebdb8;font-size:13px}.ai-orb{width:58px;height:58px;border:1px solid #52736a;border-radius:50%;display:grid;place-items:center;color:var(--lime);font:20px Georgia;box-shadow:inset 0 0 22px #c8f56012}.suggestions{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:28px}.suggestions button{border:1px solid #3d554e;background:#22302c;color:#dce5e2;border-radius:12px;padding:14px;text-align:left;cursor:pointer;font-size:12px;display:flex;justify-content:space-between}.suggestions button:hover{border-color:var(--lime)}.conversation{max-height:420px;overflow:auto;margin-top:25px;padding-right:6px}.message{display:block!important;border:0!important;padding:0!important;margin:0 0 18px!important}.message-role{font-size:10px;letter-spacing:1.4px;color:var(--lime);margin-bottom:7px;text-transform:uppercase}.message p{white-space:pre-wrap;line-height:1.75;margin:0;background:#23332e;border-radius:5px 16px 16px 16px;padding:15px;color:#edf2f0}.message.user{text-align:right}.message.user .message-role{color:#aebdb8}.message.user p{display:inline-block;background:#dfe9c8;color:var(--ink);border-radius:16px 5px 16px 16px;text-align:left}.thinking{display:flex;gap:5px;align-items:center;color:#aebdb8;font-size:12px;margin:14px 0}.thinking i{width:6px;height:6px;background:var(--lime);border-radius:50%;animation:bounce 1s infinite}.thinking i:nth-child(2){animation-delay:.15s}.thinking i:nth-child(3){animation-delay:.3s}.thinking span{margin-left:7px}@keyframes bounce{50%{transform:translateY(-5px);opacity:.5}}.ai-input{display:flex;align-items:center;margin-top:22px;background:#f7f4ed;border-radius:16px;padding:8px}.ai-input textarea{flex:1;border:0;background:transparent;resize:none;outline:none;padding:10px 12px;color:var(--ink);line-height:1.5}.ai-input button{width:42px;height:42px;border:0;border-radius:50%;background:var(--green);color:var(--lime);font-size:20px;cursor:pointer}.ai-input button:disabled{opacity:.4;cursor:not-allowed}.ai-error{color:#ffb5a4;font-size:12px;margin-top:10px}
.quota-info{color:#aebdb8;font-size:11px;text-align:right;margin-top:8px}
@media(max-width:780px){.market{display:none}.news-layout{grid-template-columns:1fr}.ticker{justify-content:flex-start}aside{order:-1}}
@media(max-width:650px){.suggestions{grid-template-columns:1fr}.ai-studio{padding:22px}.ai-orb{display:none}}
</style>
