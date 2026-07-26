<script>
export default { emits: ['navigate'] }
</script>

<template>
  <div class="home">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">Personal digital garden · 2026</p>
        <h1>记录思考，<br><i>连接</i>世界。</h1>
        <p>你好，我是张红星。这里汇集我的文章、每日资讯、数据洞察与生活工具——一个持续生长的个人数字空间。</p>
        <div class="hero-actions">
          <button @click="$emit('navigate','blog')">开始阅读 <b>→</b></button>
          <button class="ghost" @click="$emit('navigate','toolkit')">探索工具箱</button>
        </div>
      </div>
      <div class="hero-card">
        <div class="orbit o1"></div><div class="orbit o2"></div>
        <div class="monogram">ZH<span>✦</span></div>
        <p>CURIOUS MIND<br>BUILDS A BETTER LIFE</p>
      </div>
    </section>
    <section class="marquee"><span>写作 ✦ 财经 ✦ 数据 ✦ 生活 ✦ 效率 ✦ 灵感 ✦</span><span>写作 ✦ 财经 ✦ 数据 ✦ 生活 ✦ 效率 ✦ 灵感 ✦</span></section>
    <section class="portal">
      <div class="section-head"><div><p class="eyebrow">Explore</p><h2>今日从哪里开始？</h2></div><p>每个入口，都是一种看待生活的方式。</p></div>
      <div class="portal-grid">
        <article class="featured" @click="$emit('navigate','blog')"><span>01 / BLOG</span><h3>把稍纵即逝的<br>想法留下来</h3><p>技术、生活与成长随笔</p><b>阅读最新文章 ↗</b></article>
        <article @click="$emit('navigate','news')"><span>02 / PULSE</span><h3>新闻与财经</h3><p>在信息洪流中找到真正重要的信号。</p><b>查看今日简报 →</b></article>
        <article @click="$emit('navigate','analytics')"><span>03 / DATA</span><h3>数据观察室</h3><p>用更直观的方式理解趋势和变化。</p><b>进入数据中心 →</b></article>
        <article class="dark" @click="$emit('navigate','toolkit')"><span>04 / LAB</span><h3>实用工具箱</h3><p>专注计时、待办清单、灵感便签，一站完成。</p><b>立即使用 →</b></article>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero{min-height:670px;display:grid;grid-template-columns:1.1fr .9fr;align-items:center;max-width:1180px;margin:auto;padding:70px 24px 50px;gap:7vw}.hero h1{font-family:Georgia,"Songti SC",serif;font-size:clamp(58px,8vw,104px);line-height:.98;letter-spacing:-6px;margin:18px 0 28px}.hero h1 i{color:var(--green);font-weight:400}.hero-copy>p:not(.eyebrow){font-size:17px;line-height:1.8;color:var(--muted);max-width:570px}.hero-actions{display:flex;gap:12px;margin-top:34px}.hero-actions button{border:0;background:var(--green);color:white;padding:14px 22px;border-radius:999px;cursor:pointer}.hero-actions .ghost{background:transparent;color:var(--ink);border:1px solid var(--line)}.hero-card{aspect-ratio:.82;max-height:470px;position:relative;overflow:hidden;border-radius:180px 180px 24px 24px;background:#ddebaf;display:grid;place-content:center;text-align:center}.monogram{font-family:Georgia;font-size:88px;letter-spacing:-9px;color:var(--green);z-index:2}.monogram span{font-size:32px;color:#ec693d}.hero-card p{font-size:10px;letter-spacing:4px;line-height:2;z-index:2}.orbit{position:absolute;border:1px solid rgba(23,79,66,.32);border-radius:50%;inset:15%;animation:spin 18s linear infinite}.o2{inset:5% 25%;transform:rotate(55deg);animation-direction:reverse}.marquee{overflow:hidden;padding:14px 0;background:var(--green);color:var(--lime);display:flex;gap:30px;font-family:Georgia;font-size:21px;white-space:nowrap}.marquee span{animation:move 18s linear infinite}@keyframes move{to{transform:translateX(-100%)}}.portal{max-width:1180px;margin:auto;padding:90px 24px}.section-head{display:flex;justify-content:space-between;align-items:end;margin-bottom:32px}.section-head h2{font-family:Georgia,"Songti SC";font-size:40px;margin:6px 0}.section-head>p{color:var(--muted)}.portal-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.portal article{min-height:260px;border:1px solid var(--line);background:var(--paper);padding:28px;border-radius:20px;display:flex;flex-direction:column;cursor:pointer;transition:.25s}.portal article:hover{transform:translateY(-5px);box-shadow:0 14px 30px #23352a12}.portal article span{font-size:11px;letter-spacing:1.5px;color:var(--muted)}.portal h3{font-family:Georgia,"Songti SC";font-size:29px;margin:35px 0 10px}.portal article p{color:var(--muted);line-height:1.65}.portal article b{margin-top:auto;font-size:13px}.portal .featured{grid-row:span 2;min-height:534px;background:#e7edda;justify-content:flex-end}.featured h3{font-size:40px}.portal .dark{background:var(--ink);color:white}.portal .dark p,.portal .dark span{color:#aeb8b4}
@media(max-width:800px){.hero{grid-template-columns:1fr;padding-top:46px}.hero-card{display:none}.hero h1{letter-spacing:-3px}.portal-grid{grid-template-columns:1fr}.portal .featured{min-height:330px}.section-head{display:block}}
</style>
