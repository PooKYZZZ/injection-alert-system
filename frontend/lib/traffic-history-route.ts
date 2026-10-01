export type PageSearchParams = Record<string, string | string[] | undefined>

export function buildTrafficHistoryHref(searchParams: PageSearchParams): string {
  const query = new URLSearchParams()

  for (const [key, value] of Object.entries(searchParams)) {
    if (Array.isArray(value)) {
      value.forEach((entry) => query.append(key, entry))
    } else if (value !== undefined) {
      query.set(key, value)
    }
  }

  const serialized = query.toString()
  return serialized ? `/traffic-history?${serialized}` : '/traffic-history'
}
