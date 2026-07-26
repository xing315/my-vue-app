<script>
export default{
 data(){return{tab:'全部',query:'',saved:[],tabs:['全部','宏观','市场','科技','商业'],news:[
 {cat:'宏观',time:'09:30',title:'全球市场等待新一轮经济数据，风险偏好温和回升',source:'财经晨报',hot:96},
 {cat:'科技',time:'08:45',title:'人工智能应用加速落地，企业服务迎来新一轮升级',source:'科技前线',hot:91},
 {cat:'市场',time:'08:10',title:'主要指数震荡整理，新能源与消费板块表现活跃',source:'市场观察',hot:88},
 {cat:'商业',time:'昨天',title:'从产品到体验：新消费品牌正在重写增长逻辑',source:'商业评论',hot:82},
 {cat:'科技',time:'昨天',title:'端侧智能成为焦点，下一代个人设备会如何变化',source:'未来实验室',hot:79},
 {cat:'宏观',time:'07.25',title:'城市更新与服务消费释放长期发展新空间',source:'经济视野',hot:74}
 ]}},
 computed:{filtered(){return this.news.filter(n=>(this.tab==='全部'||n.cat===this.tab)&&n.title.includes(this.query))}},
 methods:{toggle(i){this.saved.includes(i)?this.saved=this.saved.filter(x=>x!==i):this.saved.push(i)}}
}
</script>
<template><div class="page-wrap news-page">
 <div class="news-hero"><div><p class="eyebrow">Daily Signal</p><h1 class="page-title">新闻财经脉搏</h1><p class="page-lead">少一点噪音，多一点信号。快速浏览值得关注的市场、科技与商业动态。</p></div><div class="market"><small>市场情绪</small><strong>72</strong><span>偏积极 ↑</span></div></div>
 <div class="ticker"><span>上证指数 <b>3,428.16</b> <i>+0.42%</i></span><span>恒生指数 <b>24,388.13</b> <i>+0.73%</i></span><span>黄金 <b>2,386.40</b> <i>+0.18%</i></span><span>USD/CNY <b>7.1523</b> <em>-0.05%</em></span></div>
 <div class="search"><span>⌕</span><input v-model="query" placeholder="搜索新闻、行业或关键词"><kbd>实时简报</kbd></div>
 <div class="filters"><button v-for="t in tabs" :class="['pill',{active:tab===t}]" @click="tab=t">{{t}}</button></div>
 <div class="news-layout"><section><article v-for="(n,i) in filtered"><div class="rank">{{String(i+1).padStart(2,'0')}}</div><div><div class="meta"><b>{{n.cat}}</b> {{n.source}} · {{n.time}}</div><h2>{{n.title}}</h2><div class="heat"><span :style="{width:n.hot+'%'}"></span></div></div><button @click="toggle(i)" :class="{saved:saved.includes(i)}" :aria-label="saved.includes(i)?'取消收藏':'收藏'">{{saved.includes(i)?'★':'☆'}}</button></article></section><aside><p class="eyebrow">Editor's Pick</p><h3>今日值得关注</h3><div class="big-num">03</div><p>宏观数据、AI 应用落地与消费复苏，是今天最值得持续追踪的三条主线。</p><hr><small>已收藏 {{saved.length}} 条资讯</small></aside></div>
</div></template>
<style scoped>
.news-hero{display:flex;justify-content:space-between;align-items:end}.market{width:150px;height:150px;border-radius:50%;border:12px solid #dce8c4;display:grid;place-content:center;text-align:center}.market strong{font:44px Georgia;color:var(--green)}.market span{font-size:11px;color:var(--green)}.ticker{margin:40px 0 18px;background:var(--ink);color:white;padding:16px 20px;border-radius:12px;display:flex;justify-content:space-between;gap:20px;overflow:auto;white-space:nowrap;font-size:12px}.ticker b{margin:0 6px}.ticker i{color:var(--lime);font-style:normal}.ticker em{color:#ff9983;font-style:normal}.search{display:flex;align-items:center;background:var(--paper);border:1px solid var(--line);border-radius:12px;padding:0 16px}.search input{flex:1;border:0;background:none;padding:16px;outline:none}.search kbd{font-size:11px;color:var(--green)}.filters{display:flex;gap:8px;margin:18px 0 28px}.news-layout{display:grid;grid-template-columns:1fr 300px;gap:24px}.news-layout section{border-top:1px solid var(--line)}article{display:grid;grid-template-columns:48px 1fr 34px;gap:16px;padding:22px 0;border-bottom:1px solid var(--line);align-items:center}.rank{font:20px Georgia;color:#a4aaa2}.meta{font-size:11px;color:var(--muted)}.meta b{color:var(--green);margin-right:9px}h2{font:22px/1.4 Georgia,"Songti SC";margin:7px 0}.heat{width:100px;height:3px;background:#ddd}.heat span{display:block;height:100%;background:#ef7354}article button{border:0;background:none;font-size:24px;cursor:pointer;color:#9ca39f}.saved{color:#e4a72e!important}aside{background:#dfe9c8;border-radius:18px;padding:28px;height:max-content}aside h3{font:27px Georgia;margin:10px 0}.big-num{font:80px Georgia;color:var(--green);line-height:1}aside p:not(.eyebrow){color:#59645f;line-height:1.7}aside hr{border:0;border-top:1px solid #bfcab0;margin:24px 0}
@media(max-width:780px){.market{display:none}.news-layout{grid-template-columns:1fr}.ticker{justify-content:flex-start}aside{order:-1}}
</style>
