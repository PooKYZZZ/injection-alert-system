export const NAV_ITEMS = [
  { label: 'Overview', href: '/dashboard' },
  { label: 'Alerts', href: '/alerts' },
  { label: 'ML Health', href: '/ml-health' },
]

export const CONFIDENCE_THRESHOLDS = {
  LOW: 0.5,
  MEDIUM: 0.8,
}

export const COLOR_MAP = {
  status: {
    high: '#dc2626',
    medium: '#f97316',
    low: '#6b7280',
    blocked: '#dc2626',
    throttled: '#f97316',
    logged: '#6b7280',
    ratelimited: '#8b5cf6',
  }
}
