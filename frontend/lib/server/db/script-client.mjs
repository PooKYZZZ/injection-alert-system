import { createClient } from '@supabase/supabase-js'

import {
  loadSupabaseScriptEnv,
  readSupabaseScriptEnv,
} from './script-env.mjs'

/**
 * Creates a service-role client for operational provisioning scripts only.
 * Never import this adapter from app runtime, auth, or client components.
 */
/**
 * @param {Record<string, string | undefined>} env
 */
export function createSupabaseScriptClient(env) {
  const values =
    env === undefined
      ? loadSupabaseScriptEnv()
      : readSupabaseScriptEnv(env)
  return createClient(values.SUPABASE_URL, values.SUPABASE_SERVICE_ROLE_KEY, {
    auth: {
      persistSession: false,
      autoRefreshToken: false,
      detectSessionInUrl: false,
    },
  })
}
