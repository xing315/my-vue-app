// 测试 Supabase 连接和认证状态
import { supabase } from './src/supabase.js'

console.log('测试 Supabase 连接...')
console.log('Supabase URL:', import.meta.env.VITE_SUPABASE_URL)
console.log('Supabase Anon Key:', import.meta.env.VITE_SUPABASE_ANON_KEY ? '已配置' : '未配置')

// 测试连接
async function testConnection() {
  try {
    // 测试认证状态
    const { data: { session } } = await supabase.auth.getSession()
    console.log('当前会话:', session)
    
    // 测试数据库连接
    const { data, error } = await supabase
      .from('transactions')
      .select('*')
      .limit(1)
    
    if (error) {
      console.error('数据库连接测试失败:', error)
    } else {
      console.log('数据库连接测试成功:', data)
    }
  } catch (error) {
    console.error('连接测试失败:', error)
  }
}

testConnection()
