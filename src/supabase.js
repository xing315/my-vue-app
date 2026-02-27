import { createClient } from '@supabase/supabase-js'

const supabaseUrl = 'https://ohnnjrbutzbkmjcdbpxt.supabase.co'
const supabaseAnonKey = 'sb_publishable_C8gUyxsyjcE595ZEo4JanQ_QGiHKNF0'

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  },
  global: {
    headers: {
      'x-client-info': 'my-vue-app/1.0.0'
    }
  }
})

// 监听认证状态变化
supabase.auth.onAuthStateChange((event, session) => {
  console.log('Supabase 认证状态变化:', event, session)
  if (session) {
    console.log('会话令牌:', session.access_token.substring(0, 20) + '...')
    console.log('用户ID:', session.user.id)
  }
})

console.log('Supabase 客户端创建成功:', {
  url: supabaseUrl,
  anonKey: supabaseAnonKey ? '已配置' : '未配置'
})
