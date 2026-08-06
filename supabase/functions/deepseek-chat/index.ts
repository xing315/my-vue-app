import { createClient } from 'npm:@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

function getUserIdFromJwt(request: Request) {
  const authorization = request.headers.get('Authorization') ?? ''
  const token = authorization.replace(/^Bearer\s+/i, '')
  const payload = token.split('.')[1]
  if (!payload) return null

  try {
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/').padEnd(
      Math.ceil(payload.length / 4) * 4,
      '=',
    )
    const decoded = JSON.parse(atob(normalized))
    return typeof decoded?.sub === 'string' ? decoded.sub : null
  } catch {
    return null
  }
}

function getShanghaiDate() {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date())
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}

function getSupabaseSecretKey() {
  const legacyKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  if (legacyKey) return legacyKey

  try {
    const keys: Record<string, unknown> = JSON.parse(
      Deno.env.get('SUPABASE_SECRET_KEYS') ?? '{}',
    )
    if (typeof keys.default === 'string') return keys.default
    const firstKey = Object.values(keys).find((value) => typeof value === 'string')
    return typeof firstKey === 'string' ? firstKey : null
  } catch {
    return null
  }
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { ...corsHeaders, 'Content-Type': 'application/json; charset=utf-8' },
  })
}

Deno.serve(async (request) => {
  if (request.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  if (request.method !== 'POST') {
    return json({ error: 'Method not allowed' }, 405)
  }

  try {
    const apiKey = Deno.env.get('DEEPSEEK_API_KEY')
    if (!apiKey) {
      return json({ error: 'DeepSeek API key is not configured' }, 503)
    }

    const allowedUserId = Deno.env.get('AI_ALLOWED_USER_ID')
    if (!allowedUserId) {
      return json({ error: 'AI owner account is not configured' }, 503)
    }

    // Supabase 网关已通过 verify_jwt 验证签名，这里再做所有者白名单判断。
    const userId = getUserIdFromJwt(request)
    if (!userId) {
      return json({ error: '请先登录后再使用 AI' }, 401)
    }
    if (userId !== allowedUserId) {
      return json({ error: '此 AI 功能仅限网站所有者使用', code: 'OWNER_ONLY' }, 403)
    }

    const supabaseUrl = Deno.env.get('SUPABASE_URL')
    const supabaseSecretKey = getSupabaseSecretKey()
    if (!supabaseUrl || !supabaseSecretKey) {
      return json({ error: 'AI 配额服务尚未配置' }, 503)
    }

    const payload = await request.json()
    const mode = payload?.mode === 'research_brief' ? 'research_brief' : 'chat'
    const incoming = Array.isArray(payload?.messages) ? payload.messages : []
    const messages: ChatMessage[] = incoming
      .filter((item: ChatMessage) =>
        (item?.role === 'user' || item?.role === 'assistant') &&
        typeof item?.content === 'string' &&
        item.content.trim().length > 0
      )
      .slice(-8)
      .map((item: ChatMessage) => ({
        role: item.role,
        content: item.content.trim().slice(0, 4000),
      }))

    const symbol = typeof payload?.symbol === 'string' && /^[036]\d{5}$/.test(payload.symbol) ? payload.symbol : null
    if (mode === 'chat' && (!messages.length || messages[messages.length - 1].role !== 'user')) {
      return json({ error: '请输入有效问题' }, 400)
    }
    if (mode === 'research_brief' && !symbol) return json({ error:'请输入有效股票代码' }, 400)

    const supabaseAdmin = createClient(supabaseUrl, supabaseSecretKey, {
      auth: { persistSession: false, autoRefreshToken: false },
    })
    const { data: quotaRows, error: quotaError } = await supabaseAdmin.rpc(
      'consume_ai_daily_quota',
      {
        p_user_id: userId,
        p_usage_date: getShanghaiDate(),
        p_daily_limit: 10,
      },
    )

    if (quotaError) {
      console.error('AI quota error:', quotaError.message)
      return json({ error: 'AI 配额检查失败，请稍后再试' }, 503)
    }

    const quota = quotaRows?.[0]
    if (!quota?.allowed) {
      return json({
        error: '今天的 10 次 AI 对话额度已用完，请明天再试',
        code: 'DAILY_LIMIT',
        remaining: 0,
      }, 429)
    }

    let researchContext: Record<string, unknown> | null = null
    if (mode === 'research_brief' && symbol) {
      const { data:stock, error:stockError } = await supabaseAdmin.from('quant_latest_scores')
        .select('symbol,name,industry,score,confidence,rating,price,change_percent,position_min,position_max,detail,trade_date,updated_at,model_version')
        .eq('symbol',symbol).single()
      if (stockError || !stock) return json({ error:'没有找到已发布的可信量化数据' }, 404)
      const { data:signals } = await supabaseAdmin.from('quant_signal_events')
        .select('trade_date,signal_type,severity,title,reason,previous_value,current_value,source')
        .eq('symbol',symbol).order('trade_date',{ascending:false}).limit(10)
      const requestedNews = Array.isArray(payload?.selectedNewsIds)
        ? payload.selectedNewsIds.filter((id:unknown)=>typeof id==='string').slice(0,5) : []
      let news: unknown[] = []
      if(requestedNews.length){
        const {data}=await supabaseAdmin.from('quant_saved_news')
          .select('news_id,title,url,source,published_at,related_symbols').eq('user_id',userId).in('news_id',requestedNews)
        news=data||[]
      }
      researchContext={stock,signals:signals||[],selectedSavedNews:news,
        trustNotice:'以上量化数据由服务端读取；没有提供的数据必须写暂无数据。'}
    }

    const system = mode === 'research_brief' ? [
      '你是A股研究简报生成器，只能使用用户消息内的服务端可信JSON。',
      '不得补充外部事实、实时新闻、目标价、收益预测或买卖指令。',
      '必须按以下六节输出：当前结论、支持证据、反面证据、近期变化、需要核实的问题、风险提示。',
      '每条事实注明来源类别和数据日期；缺失内容明确写“暂无数据”。',
    ].join('') : [
      '你是张红星个人网站中的中文知识与财经助手。',
      '回答应准确、清晰、结构化，优先使用普通人能理解的语言。',
      '你没有实时联网搜索能力，不得声称知道当前行情或刚发生的新闻。',
      '涉及时效性内容时，必须明确提醒用户核对最新可靠来源。',
      '涉及投资时给出风险提示，不提供保证收益或个性化买卖指令。',
    ].join('')
    const requestMessages = mode === 'research_brief'
      ? [{role:'user',content:`请生成研究简报。可信数据：${JSON.stringify(researchContext)}`}]
      : messages

    const response = await fetch('https://api.deepseek.com/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'deepseek-v4-flash',
        thinking: { type: 'disabled' },
        messages: [{ role:'system', content:system }, ...requestMessages],
        max_tokens: 1200,
        temperature: 0.5,
      }),
    })

    const result = await response.json()
    if (!response.ok) {
      console.error('DeepSeek API error:', response.status, result?.error?.message)
      const status = response.status === 401 ? 503 : Math.min(response.status, 599)
      return json({ error: 'AI 服务调用失败，请稍后再试' }, status)
    }

    const answer = result?.choices?.[0]?.message?.content?.trim()
    if (!answer) {
      return json({ error: 'AI 暂未返回有效内容' }, 502)
    }

    return json({
      answer,
      mode,
      symbol,
      remaining: quota.remaining_count,
      usage: {
        promptTokens: result?.usage?.prompt_tokens ?? null,
        completionTokens: result?.usage?.completion_tokens ?? null,
      },
    })
  } catch (error) {
    console.error('deepseek-chat error:', error)
    return json({ error: 'AI 服务暂时不可用' }, 500)
  }
})
