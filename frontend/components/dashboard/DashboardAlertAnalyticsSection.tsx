'use client'

import dynamic from 'next/dynamic'

const DashboardAlertAnalytics = dynamic(
  () => import('@/components/dashboard/DashboardAlertAnalytics'),
  {
    ssr: false,
    loading: () => (
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-72 animate-pulse rounded-sm border border-border-light bg-surface-light shadow-subtle"
          />
        ))}
      </div>
    ),
  }
)

export default function DashboardAlertAnalyticsSection() {
  return <DashboardAlertAnalytics />
}
