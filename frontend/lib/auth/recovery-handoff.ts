import 'server-only'

import { clearPreAuthCookie } from './preauth'
import { clearRecoveryCompletionCookie } from './recovery-cookie'

export async function clearRecoveryHandoffCookies(): Promise<void> {
  await Promise.all([
    clearPreAuthCookie(),
    clearRecoveryCompletionCookie(),
  ])
}
