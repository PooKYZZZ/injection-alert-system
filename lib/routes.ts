export interface WafRouteContract {
  path: string;
  method: 'GET' | 'POST';
  purpose: string;
  expectedParams: {
    name: string;
    type: 'query' | 'body' | 'path';
    required: boolean;
    description: string;
  }[];
  wafInspectionUseful: boolean;
  wafInspectionReason: string;
  safeExample: string;
  suspiciousExample: string;
  payloadType?: 'urlencoded' | 'json';
}

export const WAF_ROUTES: WafRouteContract[] = [
  {
    path: '/records/search',
    method: 'GET',
    purpose: 'Query indexed public land records by the portal search text',
    expectedParams: [
      { name: 'query', type: 'query', required: false, description: 'Text search string matched against seeded land-record fields' }
    ],
    wafInspectionUseful: true,
    wafInspectionReason: 'Useful for testing query parameter handling directly through the portal search form.',
    safeExample: '/records/search?query=Maple',
    suspiciousExample: '/records/search?query=%27+OR+1%3D1+--'
  },
  {
    path: '/records/[recordNo]',
    method: 'GET',
    purpose: 'Retrieve detailed profile and metadata for any specific cadastral land title',
    expectedParams: [
      { name: 'recordNo', type: 'path', required: true, description: 'Target record identification serial key (e.g. REC-2026-0001)' }
    ],
    wafInspectionUseful: true,
    wafInspectionReason: 'Useful for testing path normalization and non-alphanumeric route handling.',
    safeExample: '/records/REC-2026-0001',
    suspiciousExample: '/records/..%2f..%2f..%2f..%2fetc%2fpasswd'
  },
  {
    path: '/transactions/status',
    method: 'GET',
    purpose: 'Query real-time processing dispatch milestone tracker for certified true copies',
    expectedParams: [
      { name: 'ref', type: 'query', required: true, description: 'Alphanumeric tracking reference hash assigned at submission (e.g. TXN-100201)' }
    ],
    wafInspectionUseful: true,
    wafInspectionReason: 'Ideal for evaluating HTML escaping when input is dynamically echoed onto the response page.',
    safeExample: '/transactions/status?ref=TXN-100201',
    suspiciousExample: '/transactions/status?ref=%3Cscript%3Ealert%281%29%3C%2Fscript%3E'
  },
  {
    path: '/support/submit',
    method: 'POST',
    purpose: 'Create and persist a citizen boundary grievance or administrative dispute audit ticket',
    expectedParams: [
      { name: 'subject', type: 'body', required: true, description: 'Short grievance headline description' },
      { name: 'category', type: 'body', required: true, description: 'Dispute classification (e.g. Boundary Overlay, Typographical error)' },
      { name: 'email', type: 'body', required: true, description: 'Correspondence email contact' },
      { name: 'referenceNo', type: 'body', required: false, description: 'Cadastral reference file key linked to dispute' },
      { name: 'message', type: 'body', required: true, description: 'Comprehensive audit ticket dispute details text' }
    ],
    payloadType: 'urlencoded',
    wafInspectionUseful: true,
    wafInspectionReason: 'Allows proxy security checks to inspect multi-line POST bodies for nested SQL injection strings or shell control characters.',
    safeExample: 'subject=Incorrect+Name+Spelling&category=Typographical+Error&email=citizen%40example.net&referenceNo=REC-2026-0001&message=The+middle+initial+is+incorrectly+printed+as+Z.',
    suspiciousExample: 'subject=Attack&category=Boundary&email=test%40test.net&referenceNo=REC-123&message=%27+UNION+SELECT+null%2C+password%2C+null+FROM+users+--'
  },
  {
    path: '/appointments/submit',
    method: 'POST',
    purpose: 'Schedule a physical consultation desk reservation at a regional branch registry office',
    expectedParams: [
      { name: 'fullName', type: 'body', required: true, description: 'Legal name of the appointment applicant' },
      { name: 'email', type: 'body', required: true, description: 'Applicant business contact email' },
      { name: 'branch', type: 'body', required: true, description: 'Selected regional registry office branch (e.g. Pasig, Cainta, Marikina, Quezon City)' },
      { name: 'serviceType', type: 'body', required: true, description: 'Consultation assistance category (e.g. Boundary Verification, Deed of Sale Recording)' },
      { name: 'preferredDate', type: 'body', required: true, description: 'ISO date string requested for the reservation' },
      { name: 'notes', type: 'body', required: false, description: 'Pre-consultation requests and notes text' }
    ],
    payloadType: 'urlencoded',
    wafInspectionUseful: true,
    wafInspectionReason: 'Useful for validating string parameters in HTML forms, including detecting command injection sequences inside notes fields.',
    safeExample: 'fullName=Alice+Lee&email=alice%40example.net&branch=Pasig+Branch&serviceType=Cadastral+Survey+Verification&preferredDate=2026-07-15&notes=Retrieval+of+deeds+associated+with+tract+77A.',
    suspiciousExample: 'fullName=Tester&email=test%40test.net&branch=Pasig&serviceType=Verification&preferredDate=2026-07-15&notes=%3B+cat+%2Fetc%2Fpasswd'
  },
  {
    path: '/comments/submit',
    method: 'POST',
    purpose: 'Publish feedback or public community verification inquiries on the public message board',
    expectedParams: [
      { name: 'displayName', type: 'body', required: true, description: 'Public citizen identity nick or title alias' },
      { name: 'message', type: 'body', required: true, description: 'Feedback or remarks text that persists to SQLite' }
    ],
    payloadType: 'urlencoded',
    wafInspectionUseful: true,
    wafInspectionReason: 'Useful for checking stored content handling and HTML comment escaping.',
    safeExample: 'displayName=Public+Auditor&message=The+search+is+highly+responsive+and+the+records+load+properly%21',
    suspiciousExample: 'displayName=Attacker&message=%3Cimg+src%3Dx+onerror%3Dalert%28document.cookie%29%3E'
  },
  {
    path: '/login/submit',
    method: 'POST',
    purpose: 'Authenticate land department personnel against the registry gateway',
    expectedParams: [
      { name: 'username', type: 'body', required: true, description: 'Staff registry identity name' },
      { name: 'password', type: 'body', required: true, description: 'Secret authentication credential pin/passphrase' }
    ],
    payloadType: 'urlencoded',
    wafInspectionUseful: true,
    wafInspectionReason: 'Useful for evaluating login form validation and authentication-like request handling.',
    safeExample: 'username=officer_cainta&password=AdminSecurePass74',
    suspiciousExample: 'username=%27+OR+%271%27%3D%271&password=anything'
  },
  {
    path: '/records/[recordNo]/request-copy',
    method: 'GET',
    purpose: 'Render page with form for a Citizen True Copy (CTC) certification application',
    expectedParams: [
      { name: 'recordNo', type: 'path', required: true, description: 'Identifier of land record to request copy for' }
    ],
    wafInspectionUseful: false,
    wafInspectionReason: 'Primarily renders a static form UI, but useful for testing basic parameter manipulation.',
    safeExample: '/records/REC-2026-0001/request-copy',
    suspiciousExample: '/records/INVALID%27%22%2Frequest-copy'
  },
  {
    path: '/records/[recordNo]/request-copy/submit',
    method: 'POST',
    purpose: 'Submit and file property certification copy order, storing transactional status code',
    expectedParams: [
      { name: 'fullName', type: 'body', required: true, description: 'Applicant name for delivery tracking' },
      { name: 'email', type: 'body', required: true, description: 'Registrant email for tracking notification' },
      { name: 'purpose', type: 'body', required: true, description: 'Official legal reason for certified copy' },
      { name: 'deliveryOption', type: 'body', required: true, description: 'Delivery mechanism choice (e.g. Local Pickup, Express Mail Dispatch)' },
      { name: 'remarks', type: 'body', required: false, description: 'Optional delivery remarks text notes' }
    ],
    payloadType: 'urlencoded',
    wafInspectionUseful: true,
    wafInspectionReason: 'Routes directly to the Prisma-backed SQL database. Useful for testing form body validation in standard POST bodies.',
    safeExample: 'fullName=Marissa+Tan&email=marissa%40tan-land.com&purpose=Mortgage+Application&deliveryOption=Express+Mail+Dispatch&remarks=Deliver+to+office+hub+3.',
    suspiciousExample: 'fullName=Hacker&email=test%40test.net&purpose=Stolen&deliveryOption=Pickup&remarks=%3Cscript%3EglobalThis.cookie%3C%2Fscript%3E'
  }
];
