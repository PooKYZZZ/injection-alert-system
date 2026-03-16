export const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard', icon: 'dashboard' },
  { label: 'Alerts', href: '/alerts', icon: 'notifications' },
  { label: 'Traffic', href: '/traffic', icon: 'traffic' },
  { label: 'Mitigation Log', href: '/mitigation', icon: 'shield_lock' },
  { label: 'ML Health', href: '/ml-health', icon: 'monitor_heart' },
  { label: 'Audit Trail', href: '/audit', icon: 'history_edu' }, // moved here
] as const

export const SYSTEM_NAV_ITEMS = [] as const

export const CONFIDENCE_THRESHOLDS = {
  LOW: 0.5,
  MEDIUM: 0.8,
  HIGH: 1.0,
} as const
