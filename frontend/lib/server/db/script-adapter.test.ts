import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it, vi } from 'vitest'

describe('script-only Supabase boundary', () => {
  it('validates and trims required environment values', async () => {
    const { readSupabaseScriptEnv } = await import('./script-env.mjs')
    expect(
      readSupabaseScriptEnv({
        SUPABASE_URL: ' https://project-ref.supabase.co ',
        SUPABASE_SERVICE_ROLE_KEY: ' service-secret ',
      })
    ).toEqual({
      SUPABASE_URL: 'https://project-ref.supabase.co',
      SUPABASE_SERVICE_ROLE_KEY: 'service-secret',
    })
  })

  it('reports variable names without exposing values', async () => {
    const { readSupabaseScriptEnv } = await import('./script-env.mjs')
    const secret = 'must-not-appear'
    expect(() =>
      readSupabaseScriptEnv({ SUPABASE_SERVICE_ROLE_KEY: secret })
    ).toThrow('SUPABASE_URL')
    try {
      readSupabaseScriptEnv({
        SUPABASE_URL: 'invalid',
        SUPABASE_SERVICE_ROLE_KEY: secret,
        NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY: secret,
      })
    } catch (error) {
      expect(String(error)).not.toContain(secret)
      expect(String(error)).toContain('NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY')
    }
  })

  it('creates a non-persistent service-role client', async () => {
    vi.resetModules()
    const createClient = vi.fn(() => ({ from: vi.fn() }))
    vi.doMock('@supabase/supabase-js', () => ({ createClient }))
    const { createSupabaseScriptClient } = await import('./script-client.mjs')

    createSupabaseScriptClient({
      SUPABASE_URL: 'https://project-ref.supabase.co',
      SUPABASE_SERVICE_ROLE_KEY: 'service-secret',
    })

    expect(createClient).toHaveBeenCalledWith(
      'https://project-ref.supabase.co',
      'service-secret',
      {
        auth: {
          persistSession: false,
          autoRefreshToken: false,
          detectSessionInUrl: false,
        },
      }
    )
  })

  it('is imported only by operational scripts, never app runtime or client files', () => {
    const frontend = path.resolve(__dirname, '../..')
    const files = fs
      .readdirSync(frontend, { recursive: true })
      .filter((entry) => /\.(?:ts|tsx|mjs)$/.test(String(entry)))
      .map((entry) => path.join(frontend, String(entry)))
      .filter(
        (file) =>
          !file.includes('node_modules') &&
          !file.endsWith('script-adapter.test.ts') &&
          !file.endsWith('script-client.mjs')
      )

    for (const file of files) {
      const source = fs.readFileSync(file, 'utf8')
      if (source.includes('script-client.mjs')) {
        expect(file.includes(`${path.sep}scripts${path.sep}`)).toBe(true)
        expect(source).not.toMatch(/^['"]use client['"]/m)
      }
    }
  })
})
