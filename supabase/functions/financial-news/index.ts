const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...corsHeaders, 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } })
}

function category(text: string) {
  if (/(央行|利率|通胀|经济|财政|汇率|GDP)/i.test(text)) return '宏观'
  if (/(科技|芯片|人工智能|AI|半导体|软件)/i.test(text)) return '科技'
  if (/(公司|集团|业绩|营收|利润|收购)/i.test(text)) return '公司'
  return '市场'
}

function stripHtml(value: string) {
  return value.replace(/<[^>]*>/g, '').replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').trim()
}

Deno.serve(async (request) => {
  if (request.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })
  if (request.method !== 'POST') return json({ error: 'Method not allowed' }, 405)
  try {
    const url = new URL('https://np-weblist.eastmoney.com/comm/web/getFastNewsList')
    url.search = new URLSearchParams({ client:'web', biz:'web_724', fastColumn:'102', sortEnd:'', pageSize:'100', req_trace:String(Date.now()) }).toString()
    const response = await fetch(url, { headers: { 'User-Agent':'Mozilla/5.0', 'Referer':'https://kuaixun.eastmoney.com/' } })
    if (!response.ok) throw new Error(`Eastmoney HTTP ${response.status}`)
    const payload = await response.json()
    const rows = payload?.data?.fastNewsList ?? []
    const items = rows.map((row: Record<string, unknown>) => {
      const title=String(row.title ?? '').trim(), code=String(row.code ?? '')
      return { id:code||title, title, summary:String(row.summary ?? '').trim(), publishedAt:String(row.showTime ?? ''),
        source:'东方财富财经快讯', url:code?`https://finance.eastmoney.com/a/${code}.html`:'https://kuaixun.eastmoney.com/', category:category(title) }
    }).filter((item: {title:string}) => item.title)
    if (!items.length) throw new Error('Eastmoney empty')
    return json({ mode:'live', fetchedAt:new Date().toISOString(), source:'东方财富财经快讯', items })
  } catch (eastmoneyError) {
    try {
      const url = new URL('https://zhibo.sina.com.cn/api/zhibo/feed')
      url.search = new URLSearchParams({ page:'1', page_size:'50', zhibo_id:'152', tag_id:'0', dire:'f', dpc:'1', pagesize:'50', type:'1' }).toString()
      const response = await fetch(url)
      if (!response.ok) throw new Error(`Sina HTTP ${response.status}`)
      const payload = await response.json(), rows=payload?.result?.data?.feed?.list ?? []
      const items=rows.map((row: Record<string,unknown>, index:number)=>{const text=stripHtml(String(row.rich_text??'')); return {
        id:`sina-${row.create_time}-${index}`,title:text.slice(0,100),summary:text.slice(100),publishedAt:String(row.create_time??''),
        source:'新浪财经7×24',url:'https://finance.sina.com.cn/7x24/',category:category(text)}}).filter((item:{title:string})=>item.title)
      if (!items.length) throw new Error('Sina empty')
      return json({ mode:'live', fetchedAt:new Date().toISOString(), source:'新浪财经7×24', items })
    } catch (sinaError) {
      console.error('financial-news sources unavailable', eastmoneyError, sinaError)
      return json({ error:'实时财经新闻源暂时不可用', items:[] }, 503)
    }
  }
})
