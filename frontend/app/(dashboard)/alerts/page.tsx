import { redirect } from 'next/navigation'
import { buildTrafficHistoryHref, type PageSearchParams } from '@/lib/traffic-history-route'

export default async function LegacyAlertsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>
}) {
  redirect(buildTrafficHistoryHref(await searchParams))
}
