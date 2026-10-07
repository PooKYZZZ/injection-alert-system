const PUBLIC_SITE_HOSTNAME = 'cybertracesystems.com'

export function isPublicProjectHost(
  hostHeader: string | null | undefined
): boolean {
  const firstHost = hostHeader?.split(',')[0]?.trim()
  if (!firstHost) return false

  try {
    const hostname = new URL('http://' + firstHost).hostname
      .toLowerCase()
      .replace(/\.$/, '')
    return hostname === PUBLIC_SITE_HOSTNAME
  } catch {
    return false
  }
}