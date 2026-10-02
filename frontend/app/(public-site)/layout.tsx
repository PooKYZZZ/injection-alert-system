import type { ReactNode } from 'react'
import { headers } from 'next/headers'
import { redirect } from 'next/navigation'

import { isPublicProjectHost } from '@/lib/public-site-host'

export default async function PublicSiteLayout({
  children,
}: {
  children: ReactNode
}) {
  const requestHeaders = await headers()
  const incomingHost =
    requestHeaders.get('x-forwarded-host') || requestHeaders.get('host')

  if (!isPublicProjectHost(incomingHost)) {
    redirect('/login')
  }

  return children
}