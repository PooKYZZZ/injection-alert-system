export const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard', icon: 'dashboard' },
  { label: 'Alerts', href: '/alerts', icon: 'notifications', badge: 5 },
  { label: 'Mitigation Log', href: '/mitigation', icon: 'shield_lock' },
  { label: 'Traffic', href: '/traffic', icon: 'traffic' },
  { label: 'Rules', href: '/rules', icon: 'rule' },
  { label: 'Threat Intel', href: '/threat-intel', icon: 'travel_explore' },
  { label: 'ML Health', href: '/ml-health', icon: 'monitor_heart' },
  { label: 'Reports', href: '/reports', icon: 'assessment' },
] as const

export const SYSTEM_NAV_ITEMS = [
  { label: 'Settings', href: '/settings', icon: 'settings' },
  { label: 'Integrations', href: '/integrations', icon: 'integration_instructions' },
  { label: 'Audit Trail', href: '/audit', icon: 'history_edu' },
] as const

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
