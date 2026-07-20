export type AlertDeepLink =
  | { kind: 'none' }
  | { kind: 'valid'; id: string }
  | { kind: 'invalid' }

const POSITIVE_DECIMAL_ID = /^[1-9][0-9]*$/

export function parseAlertDeepLink(searchParams: URLSearchParams): AlertDeepLink {
  const values = searchParams.getAll('alert_id')
  if (values.length === 0) return { kind: 'none' }
  if (values.length !== 1 || !POSITIVE_DECIMAL_ID.test(values[0])) {
    return { kind: 'invalid' }
  }
  return { kind: 'valid', id: values[0] }
}

export function removeAlertDeepLink(pathWithQuery: string): string {
  const url = new URL(pathWithQuery, 'http://localhost')
  url.searchParams.delete('alert_id')
  const query = url.searchParams.toString()
  return `${url.pathname}${query ? `?${query}` : ''}${url.hash}`
}
