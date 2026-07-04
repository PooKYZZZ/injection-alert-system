import 'server-only'

import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import { readSupabaseServerEnv } from './env'

let client: SupabaseClient | undefined

export function getSupabaseServerClient(): SupabaseClient {
  if (!client) {
    const env = readSupabaseServerEnv()
    client = createClient(env.SUPABASE_URL, env.SUPABASE_SERVICE_ROLE_KEY, {
      auth: {
        autoRefreshToken: false,
        detectSessionInUrl: false,
        persistSession: false,
      },
    })
  }

  return client
}
