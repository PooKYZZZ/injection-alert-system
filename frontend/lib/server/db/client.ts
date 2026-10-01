import 'server-only'

import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import { readSupabaseServerEnv } from './env'

const SUPABASE_REQUEST_TIMEOUT_MS = 8_000

let client: SupabaseClient | undefined

export function createSupabaseFetchWithTimeout(
  timeoutMs: number,
  fetchImplementation: typeof fetch = fetch
): typeof fetch {
  return (input, init = {}) => {
    const timeoutSignal = AbortSignal.timeout(timeoutMs)
    const signal = init.signal
      ? AbortSignal.any([init.signal, timeoutSignal])
      : timeoutSignal

    return fetchImplementation(input, { ...init, signal })
  }
}

const fetchWithTimeout = createSupabaseFetchWithTimeout(
  SUPABASE_REQUEST_TIMEOUT_MS
)

export function getSupabaseServerClient(): SupabaseClient {
  if (!client) {
    const env = readSupabaseServerEnv()
    client = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
      auth: {
        autoRefreshToken: false,
        detectSessionInUrl: false,
        persistSession: false,
      },
      global: { fetch: fetchWithTimeout },
    })
  }

  return client
}
