<script>
export default{
 data(){return{tasks:JSON.parse(localStorage.getItem('zh-tasks')||'[]'),task:'',note:localStorage.getItem('zh-note')||'',seconds:25*60,running:false,timer:null}},
 computed:{clock(){return `${String(Math.floor(this.seconds/60)).padStart(2,'0')}:${String(this.seconds%60).padStart(2,'0')}`}},
 methods:{add(){if(!this.task.trim())return;this.tasks.push({text:this.task,done:false});this.task='';this.save()},save(){localStorage.setItem('zh-tasks',JSON.stringify(this.tasks))},remove(i){this.tasks.splice(i,1);this.save()},toggleTimer(){this.running=!this.running;if(this.running)this.timer=setInterval(()=>{if(this.seconds>0)this.seconds--;else this.toggleTimer()},1000);else clearInterval(this.timer)},reset(){clearInterval(this.timer);this.running=false;this.seconds=25*60},saveNote(){localStorage.setItem('zh-note',this.note)}},
 beforeUnmount(){clearInterval(this.timer)}
}
</script>
<template><div class="page-wrap">
 <p class="eyebrow">Everyday Lab</p><h1 class="page-title">效率工具箱</h1><p class="page-lead">简单、安静、随手可用。你的数据只保存在当前设备中。</p>
 <div class="tool-grid">
  <section class="focus"><div class="tool-label">01 · 专注计时</div><div class="clock">{{clock}}</div><p>{{running?'保持专注，暂时离开信息流。':'准备好后，开始一段完整的专注时间。'}}</p><div><button @click="toggleTimer">{{running?'暂停':'开始专注'}}</button><button class="secondary" @click="reset">重置</button></div></section>
  <section><div class="tool-label">02 · 今日待办</div><form @submit.prevent="add"><input v-model="task" placeholder="添加一件要完成的事…"><button>＋</button></form><ul><li v-for="(t,i) in tasks"><label><input type="checkbox" v-model="t.done" @change="save"><span :class="{done:t.done}">{{t.text}}</span></label><button @click="remove(i)">×</button></li></ul><div v-if="!tasks.length" class="placeholder">今日清单还是空的，给自己一个清晰的开始。</div></section>
  <section class="notes"><div class="tool-label">03 · 灵感便签</div><textarea v-model="note" @input="saveNote" placeholder="写下此刻的想法、灵感或一句提醒…"></textarea><small>自动保存在本机 · {{note.length}} 字</small></section>
  <section class="quick"><div class="tool-label">04 · 快捷计算</div><h2>时间转换</h2><div class="calc-row"><div><b>1</b><span>小时</span></div><strong>=</strong><div><b>60</b><span>分钟</span></div><strong>=</strong><div><b>3,600</b><span>秒</span></div></div><p>愿每一分钟，都花在真正重要的事情上。</p></section>
 </div>
</div></template>
<style scoped>
.tool-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:42px}.tool-grid section{background:var(--paper);border:1px solid var(--line);border-radius:20px;padding:28px;min-height:310px}.tool-label{font-size:11px;letter-spacing:1.6px;color:var(--green);font-weight:800}.focus{background:var(--green)!important;color:white}.clock{font:72px Georgia;margin:42px 0 5px}.focus p{color:#bbc9c5}.focus button{border:0;border-radius:999px;background:var(--lime);padding:11px 20px;margin:20px 8px 0 0;cursor:pointer}.focus .secondary{background:transparent;border:1px solid #63827a;color:white}form{display:flex;margin:25px 0 14px}form input{flex:1;padding:13px;border:1px solid var(--line);border-radius:10px 0 0 10px;outline:none}form button{border:0;background:var(--green);color:white;width:48px;border-radius:0 10px 10px 0}ul{list-style:none;padding:0;margin:0}li{display:flex;justify-content:space-between;border-bottom:1px solid var(--line);padding:11px 4px}li label{display:flex;gap:10px}li button{border:0;background:none;color:#999}.done{text-decoration:line-through;color:#aaa}.placeholder{color:var(--muted);font-size:13px;text-align:center;padding:45px 10px}.notes textarea{width:100%;height:210px;margin-top:22px;border:0;resize:none;background:#f2efe7;border-radius:12px;padding:18px;line-height:1.7;outline:none}.notes small{display:block;text-align:right;color:var(--muted);margin-top:8px}.quick{background:#e4ecd3!important}.quick h2{font:30px Georgia;margin:25px 0}.calc-row{display:flex;align-items:center;justify-content:space-between}.calc-row>div{display:grid;text-align:center}.calc-row b{font:28px Georgia}.calc-row span{font-size:11px;color:var(--muted)}.quick>p{margin-top:50px;color:var(--muted);font:16px Georgia}
@media(max-width:700px){.tool-grid{grid-template-columns:1fr}.clock{font-size:60px}}
</style>
