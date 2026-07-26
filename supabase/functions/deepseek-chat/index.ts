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

    if (!messages.length || messages[messages.length - 1].role !== 'user') {
      return json({ error: '请输入有效问题' }, 400)
    }

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

    const response = await fetch('https://api.deepseek.com/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: 'deepseek-v4-flash',
        thinking: { type: 'disabled' },
        messages: [
          {
            role: 'system',
            content: [
              '你是张红星个人网站中的中文知识与财经助手。',
              '回答应准确、清晰、结构化，优先使用普通人能理解的语言。',
              '你没有实时联网搜索能力，不得声称知道当前行情或刚发生的新闻。',
              '涉及时效性内容时，必须明确提醒用户核对最新可靠来源。',
              '涉及投资时给出风险提示，不提供保证收益或个性化买卖指令。',
            ].join(''),
          },
          ...messages,
        ],
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
