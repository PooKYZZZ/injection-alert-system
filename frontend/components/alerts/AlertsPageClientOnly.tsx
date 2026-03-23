'use client'

import dynamic from 'next/dynamic'

const AlertsPageClient = dynamic(
  () => import('@/components/alerts/AlertsPageClient').then((mod) => mod.AlertsPageClient),
  { ssr: false }
)

export function AlertsPageClientOnly() {
  return <AlertsPageClient />
}
