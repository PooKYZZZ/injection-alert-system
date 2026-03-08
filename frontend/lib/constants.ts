export const NAV_ITEMS = [
  { label: 'Overview', href: '/dashboard' },
  { label: 'Alerts', href: '/alerts' },
  { label: 'ML Health', href: '/ml-health' },
]

export const CONFIDENCE_THRESHOLDS = {
  LOW: 0.5,
  MEDIUM: 0.8,
  HIGH: 1.0,
} as const

export const COLOR_MAP = {
  severity: {
    HIGH: '#dc2626',
    MEDIUM: '#f97316',
    LOW: '#6b7280',
  },
  action: {
    BLOCKED: '#dc2626',
    THROTTLED: '#f97316',
    LOGGED: '#6b7280',
    RATE_LIMITED: '#8b5cf6',
  },
} as const
