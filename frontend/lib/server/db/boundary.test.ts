import fs from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

const frontendRoot = path.resolve(__dirname, '../../..')
const dbRoot = path.resolve(__dirname)

function sourceFiles(root: string): string[] {
  return fs.readdirSync(root, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(root, entry.name)
    if (
      entry.isDirectory() &&
      !['.next', 'coverage', 'node_modules'].includes(entry.name)
    ) {
      return sourceFiles(absolute)
    }
    return entry.isFile() && /\.(ts|tsx|js|mjs)$/.test(entry.name)
      ? [absolute]
      : []
  })
}

describe('Supabase service-role boundary', () => {
  it('keeps service-role client code under lib/server/db', () => {
    const violations = sourceFiles(frontendRoot).filter((file) => {
      if (file.startsWith(dbRoot) || file.endsWith('.test.ts')) {
        return false
      }
      return fs.readFileSync(file, 'utf8').includes('SUPABASE_SERVICE_ROLE_KEY')
    })

    expect(violations).toEqual([])
  })

  it('poisons the database client against client-side imports', () => {
    const source = fs.readFileSync(path.join(dbRoot, 'client.ts'), 'utf8')

    expect(source).toMatch(/^import 'server-only'/)
  })

  it('has no client component importing the server database boundary', () => {
    const violations = sourceFiles(frontendRoot).filter((file) => {
      const source = fs.readFileSync(file, 'utf8')
      return (
        /^\s*['"]use client['"]/m.test(source) &&
        /(?:lib\/server\/db|@\/lib\/server\/db)/.test(source)
      )
    })

    expect(violations).toEqual([])
  })
})
