export const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard', icon: 'dashboard' },
  { label: 'Alerts', href: '/alerts', icon: 'notifications' },
] as const

export const SYSTEM_NAV_ITEMS = [] as const

export const CONFIDENCE_THRESHOLDS = {
  LOW: 0.5,
  HIGH: 0.8,
} as const

// Confidence tiers per AGENTS.md:
// HIGH: > 80%, MEDIUM: 50-80%, LOW: < 50%
