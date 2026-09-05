import { PERMISSIONS, type Permission } from './auth/roles'

type NavItem = {
  label: string
  href: string
  icon: string
  requiredPermission?: Permission
}

export const NAV_ITEMS = [
  { label: 'Dashboard', href: '/dashboard', icon: 'dashboard' },
  { label: 'Alerts', href: '/alerts', icon: 'notifications' },
  {
    label: 'ML Health',
    href: '/ml-health',
    icon: 'monitor_heart',
    requiredPermission: PERMISSIONS.ML_HEALTH_READ,
  },
  {
    label: 'ML Deployment',
    href: '/ml-model',
    icon: 'model_training',
    requiredPermission: PERMISSIONS.ML_MODEL_READ,
  },
  {
    label: 'User Management',
    href: '/user-management',
    icon: 'manage_accounts',
    requiredPermission: PERMISSIONS.ACCOUNTS_READ,
  },
] satisfies readonly NavItem[]

export const SYSTEM_NAV_ITEMS = [] as const

export const CONFIDENCE_THRESHOLDS = {
  LOW: 0.5,
  HIGH: 0.8,
  CRITICAL: 0.9,
} as const

// Confidence tiers per AGENTS.md:
// CRITICAL: >= 90%, HIGH: > 80%, MEDIUM: 50-80%, LOW: < 50%
