const headers={'Content-Type':'application/json; charset=utf-8','Access-Control-Allow-Origin':'*','Cache-Control':'no-store, max-age=0'}
const category=text=>/(央行|利率|通胀|经济|财政|汇率|GDP)/i.test(text)?'宏观':/(科技|芯片|人工智能|AI|半导体|软件)/i.test(text)?'科技':/(公司|集团|业绩|营收|利润|收购)/i.test(text)?'公司':'市场'
const result=(statusCode,body)=>({statusCode,headers,body:JSON.stringify(body)})

export const handler=async()=>{
 try{
  const url=new URL('https://np-weblist.eastmoney.com/comm/web/getFastNewsList')
  url.search=new URLSearchParams({client:'web',biz:'web_724',fastColumn:'102',sortEnd:'',pageSize:'100',req_trace:String(Date.now())}).toString()
  const upstream=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0',Referer:'https://kuaixun.eastmoney.com/'}})
  if(!upstream.ok)throw new Error(`Eastmoney HTTP ${upstream.status}`)
  const payload=await upstream.json(),rows=payload?.data?.fastNewsList??[]
  const items=rows.map(row=>{const title=String(row.title??'').trim(),code=String(row.code??'');return{id:code||title,title,summary:String(row.summary??'').trim(),publishedAt:String(row.showTime??''),source:'东方财富财经快讯',url:code?`https://finance.eastmoney.com/a/${code}.html`:'https://kuaixun.eastmoney.com/',category:category(title)}}).filter(item=>item.title)
  if(!items.length)throw new Error('Eastmoney empty')
  return result(200,{mode:'live',fetchedAt:new Date().toISOString(),source:'东方财富财经快讯',items})
 }catch(eastmoneyError){
  try{
   const url=new URL('https://zhibo.sina.com.cn/api/zhibo/feed');url.search=new URLSearchParams({page:'1',page_size:'50',zhibo_id:'152',tag_id:'0',dire:'f',dpc:'1',pagesize:'50',type:'1'}).toString()
   const upstream=await fetch(url);if(!upstream.ok)throw new Error(`Sina HTTP ${upstream.status}`)
   const payload=await upstream.json(),rows=payload?.result?.data?.feed?.list??[]
   const items=rows.map((row,index)=>{const text=String(row.rich_text??'').replace(/<[^>]*>/g,'').replace(/&nbsp;/g,' ').replace(/&amp;/g,'&').trim();return{id:`sina-${row.create_time}-${index}`,title:text.slice(0,100),summary:text.slice(100),publishedAt:String(row.create_time??''),source:'新浪财经7×24',url:'https://finance.sina.com.cn/7x24/',category:category(text)}}).filter(item=>item.title)
   if(!items.length)throw new Error('Sina empty')
   return result(200,{mode:'live',fetchedAt:new Date().toISOString(),source:'新浪财经7×24',items})
  }catch(sinaError){console.error('financial news unavailable',eastmoneyError,sinaError);return result(503,{error:'实时财经新闻源暂时不可用',items:[]})}
 }
}
