import 'server-only'
import { cache } from 'react'
import { auth } from '@/auth'

// Memoizes auth() for the duration of a single server render pass.
// Use this in RSC layouts and pages instead of calling auth() directly.
export const getSession = cache(async () => {
  const session = await auth()
  return session
})
