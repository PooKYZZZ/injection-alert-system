export const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard', icon: 'dashboard' },
  { label: 'Alerts', href: '/alerts', icon: 'notifications' },
  { label: 'ML Health', href: '/ml-health', icon: 'monitor_heart' },
] as const

export const SYSTEM_NAV_ITEMS = [] as const

export const CONFIDENCE_THRESHOLDS = {
  LOW: 0.5,
  HIGH: 0.8,
  CRITICAL: 0.9,
} as const

// Confidence tiers per AGENTS.md:
// CRITICAL: >= 90%, HIGH: > 80%, MEDIUM: 50-80%, LOW: < 50%
