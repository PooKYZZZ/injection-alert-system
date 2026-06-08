export interface SupportTicket {
  referenceNo: string;
  email: string;
  category: string;
  subject: string;
  message: string;
  timestamp: string;
  status: string;
}

export interface Appointment {
  referenceNo: string;
  fullName: string;
  email: string;
  branch: string;
  serviceType: string;
  preferredDate: string;
  notes: string;
  timestamp: string;
  status: string;
}

export interface CertifiedCopyRequest {
  referenceNo: string;
  recordNo: string;
  fullName: string;
  email: string;
  purpose: string;
  deliveryOption: string;
  remarks: string;
  timestamp: string;
  status: string;
}

export interface CitizenComment {
  displayName: string;
  message: string;
  timestamp: string;
}

// Simple deterministic generator based on standard timestamp or random indexes
export function generateRefNo(prefix: string): string {
  // Generates something like SUP-2026-4821 or APT-2026-1049
  const year = 2026;
  const num = Math.floor(1000 + Math.random() * 9000);
  return `${prefix}-${year}-${num}`;
}
