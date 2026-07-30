// Setup type definitions for built-in Supabase Runtime APIs
import 'jsr:@supabase/functions-js/edge-runtime.d.ts'
import { withSupabase } from 'jsr:@supabase/server@^1'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type, x-app-id, x-app-version, x-device-id, x-session-id',
  'Access-Control-Allow-Methods': 'POST, OPTIONS'
}

const allowedTypes = new Set([
  'startup', 'method', 'page_resume', 'page_pause', 'click', 'block', 'aop_enter', 'aop_exit'
])
const normalizeType = (value: unknown) => value === 'main_thread_block' ? 'block' : text(value, 50)
const text = (value: unknown, max = 500) =>
  typeof value === 'string' && value.trim() ? value.trim().slice(0, max) : null
const number = (value: unknown) => {
  const parsed = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null
}
const timestamp = (value: unknown) => {
  const parsed = typeof value === 'number' ? value : Date.parse(String(value))
  if (!Number.isFinite(parsed)) return null
  return parsed >= Date.parse('2020-01-01T00:00:00Z') && parsed <= Date.now() + 86_400_000
    ? new Date(parsed).toISOString() : null
}

export default {
  fetch: withSupabase({ auth: 'none' }, async (request, context) => {
    if (request.method === 'OPTIONS') return new Response('ok', { headers: corsHeaders })
    if (request.method !== 'POST') {
      return Response.json({ error: 'method_not_allowed' }, { status: 405, headers: corsHeaders })
    }
    if (Number(request.headers.get('content-length') || 0) > 1_000_000) {
      return Response.json({ error: 'payload_too_large' }, { status: 413, headers: corsHeaders })
    }
    const ingestKey = Deno.env.get('APP_TELEMETRY_INGEST_KEY')
    if (ingestKey && request.headers.get('x-ingest-key') !== ingestKey) {
      return Response.json({ error: 'unauthorized' }, { status: 401, headers: corsHeaders })
    }

    try {
      const payload = await request.json()
      const items = Array.isArray(payload) ? payload : payload?.events
      if (!Array.isArray(items) || items.length === 0 || items.length > 500) {
        return Response.json({ error: 'events_must_be_an_array_of_1_to_500_items' }, { status: 400, headers: corsHeaders })
      }

    const headerAppId = text(request.headers.get('x-app-id'), 150) || 'com.example.mystudy'
    const headerAppVersion = text(request.headers.get('x-app-version'), 50)
    const headerDeviceId = text(request.headers.get('x-device-id'), 150)
    const headerSessionId = text(request.headers.get('x-session-id'), 150)
    const batchId = crypto.randomUUID()
    const rows = items.map((event: Record<string, unknown>, index: number) => {
      const eventType = normalizeType(event.type)
      const eventTime = timestamp(event.timestamp)
      if (!eventType || !allowedTypes.has(eventType) || !eventTime) {
        throw new Error(`invalid_event_at_index_${index}`)
      }
      const known = new Set([
        'type', 'timestamp', 'eventId', 'appId', 'appVersion', 'buildType', 'platform',
        'deviceId', 'sessionId', 'page', 'method', 'view', 'id', 'costMs', 'tag',
        'permission', 'allowed'
      ])
      const metadata: Record<string, unknown> =
        Object.fromEntries(Object.entries(event).filter(([key]) => !known.has(key)))
      if (text(event.eventId, 100)) metadata.eventId = text(event.eventId, 100)
      return {
        event_type: eventType,
        event_time: eventTime,
        app_id: text(event.appId, 150) || headerAppId,
        app_version: text(event.appVersion, 50) || headerAppVersion,
        build_type: text(event.buildType, 30),
        platform: text(event.platform, 30) || 'android',
        device_id: text(event.deviceId, 150) || headerDeviceId,
        session_id: text(event.sessionId, 150) || headerSessionId,
        batch_id: batchId,
        page: text(event.page),
        method: text(event.method),
        view_type: text(event.view, 100),
        view_id: text(event.id, 200),
        cost_ms: number(event.costMs),
        tag: text(event.tag, 200),
        permission: text(event.permission, 200),
        allowed: typeof event.allowed === 'boolean' ? event.allowed : null,
        metadata
      }
    })

      const { error } = await context.supabaseAdmin
        .from('app_telemetry_events')
        .insert(rows)
      if (error) throw error
      return Response.json(
        { accepted: rows.length, batchId, receivedAt: new Date().toISOString() },
        { status: 202, headers: { ...corsHeaders, 'Cache-Control': 'no-store' } }
      )
    } catch (error) {
      const invalid = error instanceof Error && error.message.startsWith('invalid_event_')
      console.error('app-events ingestion failed', error)
      return Response.json(
        { error: invalid ? error.message : 'ingestion_failed' },
        { status: invalid ? 400 : 500, headers: corsHeaders }
      )
    }
  })
}
