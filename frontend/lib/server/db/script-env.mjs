/**
 * Environment validation for operational provisioning scripts only.
 * App runtime code uses the server-only TypeScript boundary instead.
 */
/**
 * @param {Record<string, string | undefined>} env
 */
export function readSupabaseScriptEnv(env = process.env) {
  const invalid = []
  const url = env.SUPABASE_URL?.trim()
  const serviceKey = env.SUPABASE_SERVICE_ROLE_KEY?.trim()

  try {
    if (!url || new URL(url).protocol !== 'https:') invalid.push('SUPABASE_URL')
  } catch {
    invalid.push('SUPABASE_URL')
  }
  if (!serviceKey) invalid.push('SUPABASE_SERVICE_ROLE_KEY')
  if (env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY?.trim()) {
    invalid.push('NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY')
  }
  if (invalid.length > 0) {
    throw new Error(
      `Invalid server environment: ${[...new Set(invalid)].join(', ')}`
    )
  }

  return {
    SUPABASE_URL: url,
    SUPABASE_SERVICE_ROLE_KEY: serviceKey,
  }
}
