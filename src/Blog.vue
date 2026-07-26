<script>
export default {
  data(){return{active:'全部',query:'',selected:null,cats:['全部','技术手记','生活随笔','成长思考'],posts:[
    {id:1,cat:'成长思考',date:'2026.07.20',title:'在快时代，重新练习缓慢思考',excerpt:'真正有价值的答案，往往不会在第一个念头里出现。关于注意力、阅读与独处的几条笔记。',time:'6 min',color:'#dfe8c7'},
    {id:2,cat:'技术手记',date:'2026.07.12',title:'我如何搭建自己的数字花园',excerpt:'从信息收集到持续输出，一套不过度复杂、却能长期运行的个人知识系统。',time:'9 min',color:'#d9e7e8'},
    {id:3,cat:'生活随笔',date:'2026.06.28',title:'夏日傍晚的城市漫游',excerpt:'没有目的地的散步，是成年人少有的自由。沿着旧街道，重新认识生活的附近。',time:'4 min',color:'#f2d7c8'},
    {id:4,cat:'技术手记',date:'2026.06.16',title:'AI 时代，什么仍值得亲手完成？',excerpt:'工具越来越聪明，我们反而更需要知道自己的判断、品味与责任在哪里。',time:'7 min',color:'#e5ddf0'},
    {id:5,cat:'成长思考',date:'2026.05.30',title:'把一年拆成十二次小实验',excerpt:'比宏大目标更有效的，是低成本、可复盘、能积累的小型人生实验。',time:'5 min',color:'#f0e6b7'}
  ]}},
  computed:{filtered(){return this.posts.filter(p=>(this.active==='全部'||p.cat===this.active)&&(`${p.title}${p.excerpt}`).includes(this.query))}}
}
</script>
<template>
  <div class="page-wrap blog-page">
    <p class="eyebrow">Words & Notes</p><h1 class="page-title">文章与随笔</h1>
    <p class="page-lead">记录技术的锋芒，也收藏生活的纹理。所有认真想过的事情，都值得被好好写下来。</p>
    <div class="blog-tools"><div class="filters"><button v-for="c in cats" :class="['pill',{active:active===c}]" @click="active=c">{{c}}</button></div><input v-model="query" placeholder="搜索文章…"></div>
    <div class="post-list">
      <article v-for="(p,i) in filtered" :key="p.id" @click="selected=p">
        <div class="post-num">0{{i+1}}</div><div class="post-art" :style="{background:p.color}"><span>✦</span></div>
        <div class="post-copy"><div><b>{{p.cat}}</b><span>{{p.date}} · {{p.time}}</span></div><h2>{{p.title}}</h2><p>{{p.excerpt}}</p></div><button>↗</button>
      </article>
      <div v-if="!filtered.length" class="empty">没有找到相关文章，换个关键词试试。</div>
    </div>
    <div v-if="selected" class="modal" @click.self="selected=null"><article><button @click="selected=null">×</button><p class="eyebrow">{{selected.cat}} · {{selected.date}}</p><h2>{{selected.title}}</h2><p>{{selected.excerpt}}</p><p>这是文章阅读预览。完整内容正在持续整理中，好的文字值得慢慢写，也值得慢慢读。</p><blockquote>“建立自己的思考坐标，才不会被时代的速度轻易带走。”</blockquote></article></div>
  </div>
</template>
<style scoped>
.blog-tools{display:flex;justify-content:space-between;gap:20px;margin:42px 0 20px}.filters{display:flex;gap:8px;flex-wrap:wrap}.blog-tools input{width:220px;border:1px solid var(--line);background:var(--paper);border-radius:999px;padding:10px 16px;outline:none}.post-list{border-top:1px solid var(--line)}.post-list>article{display:grid;grid-template-columns:45px 120px 1fr 40px;gap:24px;align-items:center;padding:25px 0;border-bottom:1px solid var(--line);cursor:pointer}.post-num{font-family:Georgia;color:var(--muted)}.post-art{height:90px;border-radius:12px;display:grid;place-items:center;font-size:28px;color:var(--green)}.post-copy>div{display:flex;gap:14px;font-size:11px}.post-copy b{color:var(--green)}.post-copy span{color:var(--muted)}h2{font-family:Georgia,"Songti SC";font-size:25px;margin:8px 0}p{color:var(--muted);line-height:1.6;margin:0}.post-list article>button{border:0;background:none;font-size:20px}.empty{text-align:center;padding:70px;color:var(--muted)}.modal{position:fixed;inset:0;background:#17231fcc;z-index:200;display:grid;place-items:center;padding:20px}.modal article{background:var(--paper);max-width:650px;padding:48px;border-radius:24px;position:relative}.modal article>button{position:absolute;right:20px;top:15px;border:0;background:none;font-size:28px;cursor:pointer}.modal h2{font-size:38px}.modal p{font-size:17px;margin:20px 0}.modal blockquote{margin:28px 0 0;border-left:3px solid var(--lime);padding:12px 20px;font-family:Georgia;font-size:20px}
@media(max-width:650px){.blog-tools{display:block}.blog-tools input{margin-top:14px;width:100%}.post-list>article{grid-template-columns:34px 1fr}.post-art{display:none}.post-list article>button{display:none}}
</style>
