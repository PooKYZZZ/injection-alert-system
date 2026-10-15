import { ALERT_CONFIDENCE_HELP_TEXT } from '@/features/alerts/help-text'

export interface ProductTourStep {
  id: string
  title: string
  description: string
  target?: string
}

export interface ProductTourDefinition {
  id: string
  title: string
  description: string
  steps: readonly ProductTourStep[]
}

const DASHBOARD_TOUR: ProductTourDefinition = {
  id: 'dashboard',
  title: 'Dashboard tour',
  description: 'A quick walkthrough of the security activity summary.',
  steps: [
    {
      id: 'overview',
      title: 'Dashboard overview',
      target: 'dashboard-overview',
      description:
        'This page summarizes current system activity and security monitoring information for the selected rolling window.',
    },
    {
      id: 'actionable-detections',
      title: 'Actionable detections',
      target: 'dashboard-actionable-detections',
      description:
        'This count shows persisted records with an actionable attack classification that may need administrator or analyst attention.',
    },
    {
      id: 'recorded-blocked',
      title: 'Recorded blocked requests',
      target: 'dashboard-recorded-blocked',
      description:
        'This card counts records whose saved action label is BLOCKED. It describes recorded data, not proof of a runtime WAF block.',
    },
    {
      id: 'recorded-throttled',
      title: 'Recorded throttled requests',
      target: 'dashboard-recorded-throttled',
      description:
        'This card counts stored records with a THROTTLED action label. It does not by itself prove that a request was slowed at runtime.',
    },
    {
      id: 'traffic-records',
      title: 'Traffic records',
      target: 'dashboard-traffic-records',
      description:
        'Traffic records are stored request-log rows in the selected window. Related records may come from the same request.',
    },
    {
      id: 'time-window',
      title: 'Choose the time window',
      target: 'dashboard-time-window',
      description:
        'Use these controls to switch the rolling period used by the summary cards, chart, and dashboard activity breakdown.',
    },
    {
      id: 'request-overview',
      title: 'Request overview',
      target: 'dashboard-timeline',
      description:
        'The timeline shows recorded ALLOWED, THROTTLED, and BLOCKED action labels over time. These series do not by themselves prove the HTTP outcome.',
    },
    {
      id: 'confidence-information',
      title: 'Confidence and policy information',
      target: 'dashboard-breakdown',
      description:
        'Open the Attack and model breakdown to inspect attack types, confidence tiers, policy context, top sources, and targeted paths.',
    },
    {
      id: 'recent-history',
      title: 'Recent activity and history',
      target: 'dashboard-recent-history',
      description:
        'Review the most recent detections here, then open Traffic History for searching, filtering, and full request details.',
    },
  ],
}

const HISTORY_TOUR: ProductTourDefinition = {
  id: 'traffic-history',
  title: 'Traffic History tour',
  description: 'Learn how to find and investigate recorded traffic events.',
  steps: [
    {
      id: 'overview',
      title: 'Traffic History overview',
      target: 'history-filters',
      description:
        'Traffic History contains previously recorded requests and security detections that you can search, filter, and inspect.',
    },
    {
      id: 'search',
      title: 'Search records',
      target: 'history-search',
      description:
        'Search by the available traffic context to find a specific request or detection. The results update without leaving this page.',
    },
    {
      id: 'filters',
      title: 'Filter the results',
      target: 'history-filters',
      description:
        'Use the filter controls for triage state, time window, recorded action, confidence, and optional normal traffic.',
    },
    {
      id: 'table',
      title: 'Traffic history table',
      target: 'history-table',
      description:
        'Each row represents a stored traffic record or security event. Select a row to open its detailed review drawer.',
    },
    {
      id: 'classification',
      title: 'Attack or detection type',
      target: 'history-prediction-column',
      description:
        'Prediction is the classification saved for the record. It is not a severity rating or proof of malicious intent by itself.',
    },
    {
      id: 'confidence',
      title: 'Confidence',
      target: 'history-confidence-column',
      description:
        'Confidence describes how strongly the model supports the displayed classification, using the project confidence tiers.',
    },
    {
      id: 'status-action',
      title: 'Status and recorded action',
      target: 'history-action-column',
      description:
        'These fields show the saved triage status and recorded action. They do not independently confirm which layer enforced a request.',
    },
    {
      id: 'details',
      title: 'Open traffic details',
      target: 'history-details-column',
      description:
        'Click a record or its details control to inspect the request evidence retained for that traffic event.',
    },
    {
      id: 'pagination',
      title: 'Move through results',
      target: 'history-pagination',
      description:
        'Use the pagination controls to move through the complete Traffic History result set.',
    },
  ],
}

const USER_MANAGEMENT_TOUR: ProductTourDefinition = {
  id: 'user-management',
  title: 'User Management tour',
  description: 'Learn how administrators review and manage account access.',
  steps: [
    {
      id: 'overview',
      title: 'User Management overview',
      target: 'user-management-overview',
      description:
        'Administrators can review system users, account access, and MFA enrollment state from this page.',
    },
    {
      id: 'user-list',
      title: 'User list',
      target: 'user-management-list',
      description:
        'Each row represents one registered user and summarizes their account, role, lifecycle state, and MFA status.',
    },
    {
      id: 'search',
      title: 'Search and filter users',
      target: 'user-management-search',
      description:
        'Search by name, email, role, or account state to quickly locate the user you need to review.',
    },
    {
      id: 'invite',
      title: 'Invite a user',
      target: 'user-management-invite',
      description:
        'Invite user creates an account and queues a short-lived password setup link for the selected access role.',
    },
    {
      id: 'roles',
      title: 'User roles',
      target: 'user-management-role-column',
      description:
        'The role controls which areas and administrative actions are available to an account.',
    },
    {
      id: 'status',
      title: 'User status',
      target: 'user-management-status-column',
      description:
        'Lifecycle status shows whether the account is active, waiting for password setup, or disabled.',
    },
    {
      id: 'details',
      title: 'Open user details',
      target: 'user-management-row',
      description:
        'Click anywhere on a user row to open the details sidebar. Keyboard users can focus the Account button in that row and press Enter.',
    },
    {
      id: 'administrative-actions',
      title: 'Manage account access',
      target: 'user-management-mfa-column',
      description:
        'After opening a row, authorized administrators can use the sidebar to edit roles, change email, reset MFA, resend setup, or suspend access when those actions apply.',
    },
  ],
}

const GENERAL_TOUR: ProductTourDefinition = {
  id: 'general',
  title: 'Help & Guide',
  description: 'A quick guide to the main CyberTrace workspace areas and evidence.',
  steps: [
    {
      id: 'getting-started',
      title: 'Getting started',
      description:
        'Use the sidebar to move between Dashboard, Traffic History, and the tools available to your role. Open Help again at any time to restart this walkthrough.',
    },
    {
      id: 'review-detections',
      title: 'Review a detection',
      description:
        'Open a Traffic History row to inspect its request details, model result, related WAF evidence, and available triage controls. The controls available depend on your role.',
    },
    {
      id: 'confidence',
      title: 'Confidence',
      description: ALERT_CONFIDENCE_HELP_TEXT,
    },
    {
      id: 'waf-evidence',
      title: 'WAF evidence',
      description:
        'Correlated ModSecurity/CRS records can show matched rules and an anomaly score. A missing CRS match means no matching WAF evidence was returned; it does not by itself invalidate a model result.',
    },
    {
      id: 'recorded-action',
      title: 'Recorded action and observed outcome',
      description:
        'A recorded action is a label stored on the record. An observed HTTP status is the response reported by its producer. The status alone does not identify which system layer enforced a decision.',
    },
    {
      id: 'source-verification',
      title: 'Source verification',
      description:
        'Source origin names the address source accepted by the backend, such as a verified Cloudflare connecting IP or the direct remote address. Verification describes whether configured checks accepted that evidence; it does not identify a person behind the address.',
    },
  ],
}

export function getProductTourDefinition(pathname: string | null | undefined): ProductTourDefinition {
  if (pathname === '/dashboard' || pathname?.startsWith('/dashboard/')) {
    return DASHBOARD_TOUR
  }
  if (
    pathname === '/traffic-history' ||
    pathname?.startsWith('/traffic-history/') ||
    pathname === '/alerts' ||
    pathname?.startsWith('/alerts/')
  ) {
    return HISTORY_TOUR
  }
  if (
    pathname === '/user-management' ||
    pathname?.startsWith('/user-management/')
  ) {
    return USER_MANAGEMENT_TOUR
  }
  return GENERAL_TOUR
}
