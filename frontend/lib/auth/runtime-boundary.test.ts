import fs from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

const frontendRoot = path.resolve(__dirname, '../..')

describe('runtime authentication boundary', () => {
  it('has no AUTH_USERS_JSON registry or fallback in runtime auth code', () => {
    const authRuntimeFiles = [
      path.join(frontendRoot, 'auth.ts'),
      ...fs
        .readdirSync(path.resolve(__dirname), { withFileTypes: true })
        .filter(
          (entry) =>
            entry.isFile() &&
            entry.name.endsWith('.ts') &&
            !entry.name.endsWith('.test.ts')
        )
        .map((entry) => path.resolve(__dirname, entry.name)),
      path.join(frontendRoot, 'lib/server/db/auth-accounts.ts'),
    ]
    const forbidden = /AUTH_USERS_JSON|readAccountRegistry|findAccountByIdentifier/

    const violations = authRuntimeFiles.filter((file) =>
      forbidden.test(fs.readFileSync(file, 'utf8'))
    )

    expect(violations).toEqual([])
  })
})
