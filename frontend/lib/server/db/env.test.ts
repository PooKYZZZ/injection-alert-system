import { afterEach, describe, expect, it, vi } from 'vitest'

import { readSupabaseServerEnv } from './env'

const validEnv = {
  SUPABASE_URL: 'https://project-ref.supabase.co',
  SUPABASE_SERVICE_ROLE_KEY: 'test-service-role-secret',
}

describe('readSupabaseServerEnv', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it.each(['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY'] as const)(
    'fails closed when %s is missing',
    (name) => {
      const env = { ...validEnv }
      delete env[name]

      expect(() => readSupabaseServerEnv(env)).toThrow(name)
    }
  )

  it('rejects a public service-role key variable', () => {
    expect(() =>
      readSupabaseServerEnv({
        ...validEnv,
        NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY: 'public-secret',
      })
    ).toThrow('NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY')
  })

  it('rejects a whitespace-only service-role key', () => {
    expect(() =>
      readSupabaseServerEnv({
        ...validEnv,
        SUPABASE_SERVICE_ROLE_KEY: '   ',
      })
    ).toThrow('SUPABASE_SERVICE_ROLE_KEY')
  })

  it('trims valid server-only values', () => {
    expect(
      readSupabaseServerEnv({
        SUPABASE_URL: `  ${validEnv.SUPABASE_URL}  `,
        SUPABASE_SERVICE_ROLE_KEY: `  ${validEnv.SUPABASE_SERVICE_ROLE_KEY}  `,
      })
    ).toEqual(validEnv)
  })

  it('does not log or expose secret values when validation fails', () => {
    const consoleSpies = [
      vi.spyOn(console, 'log').mockImplementation(() => undefined),
      vi.spyOn(console, 'info').mockImplementation(() => undefined),
      vi.spyOn(console, 'warn').mockImplementation(() => undefined),
      vi.spyOn(console, 'error').mockImplementation(() => undefined),
    ]
    const secret = 'must-never-appear'

    let message = ''
    try {
      readSupabaseServerEnv({
        SUPABASE_URL: 'not-a-url',
        SUPABASE_SERVICE_ROLE_KEY: secret,
      })
    } catch (error) {
      message = error instanceof Error ? error.message : String(error)
    }

    expect(message).not.toContain(secret)
    for (const spy of consoleSpies) {
      expect(spy).not.toHaveBeenCalled()
    }
  })

  it('does not expose a forbidden public secret value', () => {
    const publicSecret = 'must-never-appear-publicly'

    expect(() =>
      readSupabaseServerEnv({
        ...validEnv,
        NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY: publicSecret,
      })
    ).toThrowError(
      expect.objectContaining({
        message: expect.not.stringContaining(publicSecret),
      })
    )
  })
})
