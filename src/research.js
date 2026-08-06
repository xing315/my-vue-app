import { supabase } from './supabase.js'

export const localHoldings = () => {
  try { return JSON.parse(localStorage.getItem('quant-holdings') || '[]') } catch { return [] }
}

export async function ensureDefaultAlertRules(user){
  if(!user)return
  const {count,error}=await supabase.from('quant_alert_rules').select('id',{count:'exact',head:true}).eq('user_id',user.id)
  if(error)throw error;if(count)return
  const defaults=[['score_threshold',70],['score_change',5],['top30_change',null],['ma_break',null],['risk_change',null],['holding_downgrade',null],['related_news',null]]
  const {error:insertError}=await supabase.from('quant_alert_rules').insert(defaults.map(([rule_type,threshold])=>({user_id:user.id,rule_type,threshold})))
  if(insertError)throw insertError
}

export async function loadResearchState(user) {
  if (!user) return { watchlist:[], holdings:localHoldings(), alerts:[], savedNews:[] }
  const [watch,holdings,alerts,saved] = await Promise.all([
    supabase.from('quant_watchlist').select('symbol,created_at').order('created_at'),
    supabase.from('quant_holdings').select('id,symbol,name,cost,shares,created_at').order('created_at'),
    supabase.from('quant_user_alerts').select('signal_id,read_at,created_at,signal:quant_signal_events(*)').order('created_at',{ascending:false}).limit(100),
    supabase.from('quant_saved_news').select('news_id,title,url,source,published_at,related_symbols,created_at').order('created_at',{ascending:false}),
  ])
  const firstError=[watch,holdings].find(result=>result.error)?.error
  if(firstError) throw firstError
  return {watchlist:(watch.data||[]).map(row=>row.symbol),holdings:(holdings.data||[]).map(row=>({...row,code:row.symbol,cost:Number(row.cost)})),
    alerts:alerts.error?[]:(alerts.data||[]).map(row=>({...row.signal,signalId:row.signal_id,readAt:row.read_at,inboxCreatedAt:row.created_at})),savedNews:saved.error?[]:(saved.data||[])}
}

export async function migrateLocalHoldings(user) {
  const local=localHoldings()
  if(!user||!local.length||localStorage.getItem('quant-holdings-migrated')) return false
  if(!confirm(`检测到本机保存的 ${local.length} 条持仓，是否同步到云端？本机备份会继续保留。`)) {
    localStorage.setItem('quant-holdings-migrated','skipped'); return false
  }
  const rows=local.filter(h=>/^[036]\d{5}$/.test(h.code)&&Number(h.cost)>0&&Number(h.shares)>0)
    .map(h=>({user_id:user.id,symbol:h.code,name:h.name||h.code,cost:Number(h.cost),shares:Number(h.shares)}))
  if(rows.length){const {error}=await supabase.from('quant_holdings').insert(rows);if(error)throw error}
  localStorage.setItem('quant-holdings-migrated','done');return true
}

export async function toggleWatchlist(user, symbol, active) {
  if(!user) throw new Error('请先登录后使用云端自选股')
  const result=active?await supabase.from('quant_watchlist').delete().eq('user_id',user.id).eq('symbol',symbol)
    :await supabase.from('quant_watchlist').insert({user_id:user.id,symbol})
  if(result.error) throw result.error
}

export async function addCloudHolding(user, holding) {
  if(!user) throw new Error('请先登录后同步持仓')
  const {data,error}=await supabase.from('quant_holdings').insert({user_id:user.id,symbol:holding.code,name:holding.name,
    cost:holding.cost,shares:holding.shares}).select('id,symbol,name,cost,shares').single()
  if(error)throw error;return {...data,code:data.symbol,cost:Number(data.cost)}
}

export async function removeCloudHolding(user,id){
  const {error}=await supabase.from('quant_holdings').delete().eq('user_id',user.id).eq('id',id);if(error)throw error
}

export async function markAlertRead(user,signalId){
  const {error}=await supabase.from('quant_user_alerts').update({read_at:new Date().toISOString()}).eq('user_id',user.id).eq('signal_id',signalId)
  if(error)throw error
}

export async function toggleSavedNews(user,item,isSaved){
  if(!user) throw new Error('请先登录后收藏资讯')
  const query=isSaved?supabase.from('quant_saved_news').delete().eq('user_id',user.id).eq('news_id',item.id)
    :supabase.from('quant_saved_news').upsert({user_id:user.id,news_id:item.id,title:item.title,url:item.url||null,source:item.source,
      published_at:item.publishedAt||null,related_symbols:item.relatedSymbols||[]},{onConflict:'user_id,news_id'})
  const {error}=await query;if(error)throw error
}
