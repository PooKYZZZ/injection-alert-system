import { z } from 'zod'

const supabaseServerEnvSchema = z
  .object({
    SUPABASE_URL: z.string().trim().url(),
    SUPABASE_SERVICE_ROLE_KEY: z.string().trim().min(1),
    NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY: z.string().optional(),
  })
  .superRefine((env, context) => {
    if (env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY) {
      context.addIssue({
        code: 'custom',
        path: ['NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY'],
        message:
          'NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY is forbidden; the service-role key must remain server-only',
      })
    }
  })

export type SupabaseServerEnv = {
  SUPABASE_URL: string
  SUPABASE_SERVICE_ROLE_KEY: string
}

export function readSupabaseServerEnv(
  env: NodeJS.ProcessEnv | Record<string, string | undefined> = process.env
): SupabaseServerEnv {
  const result = supabaseServerEnvSchema.safeParse(env)
  if (!result.success) {
    const names = [
      ...new Set(
        result.error.issues.map((issue) => String(issue.path[0] ?? 'environment'))
      ),
    ]
    throw new Error(`Invalid server environment: ${names.join(', ')}`)
  }

  return {
    SUPABASE_URL: result.data.SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY: result.data.SUPABASE_SERVICE_ROLE_KEY,
  }
}
