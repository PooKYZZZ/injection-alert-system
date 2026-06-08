/**
 * Public-facing statuses and styles for the status tracker.
 * Maps raw status strings to clean public-service terms, visual styling, and next steps.
 */

export interface PublicStatusInfo {
  label: string;
  description: string;
  badgeStyle: string; // Tailwind styling classes
  nextAction: string;
}

export const STATUS_MAPPINGS: Record<string, PublicStatusInfo> = {
  // Formal service statuses requested in guidelines
  "PENDING_REVIEW": {
    label: "Pending Review",
    description: "The submitted request is waiting for review by the demo registry team.",
    badgeStyle: "bg-amber-50 text-amber-900 border-amber-300",
    nextAction: "No action required. Registry staff will process this within 1-2 administrative days.",
  },
  "UNDER_PROCESSING": {
    label: "Under Processing",
    description: "The request is being reviewed against sample land records.",
    badgeStyle: "bg-blue-50 text-blue-900 border-blue-300",
    nextAction: "Keep your reference number at hand for updates.",
  },
  "FOR_VERIFICATION": {
    label: "For Verification",
    description: "The sample coordinates are being checked for consistency.",
    badgeStyle: "bg-purple-50 text-purple-900 border-purple-300",
    nextAction: "No active verification items are requested from the submitting citizen.",
  },
  "QUEUED": {
    label: "Queued",
    description: "Your document request is waiting in the processing queue.",
    badgeStyle: "bg-slate-100 text-slate-800 border-slate-350",
    nextAction: "The demo copy summary will be prepared soon.",
  },
  "READY_FOR_PICKUP": {
    label: "Ready for Pickup",
    description: "The printed certified copy is ready in the selected demo branch.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "Visit your selected branch during municipal office hours to collect your hard copy.",
  },
  "RELEASED": {
    label: "Released",
    description: "The requested sample record packet has been released.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "Review the released sample record packet.",
  },
  "DELIVERED": {
    label: "Delivered",
    description: "The digital copy summary has been prepared.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "Review the demo copy summary in this portal.",
  },
  "REQUEST_RECEIVED": {
    label: "Request Received",
    description: "Your submission has been saved in the demo processing queue.",
    badgeStyle: "bg-blue-50 text-blue-950 border-blue-300",
    nextAction: "The requested deed copy is being prepared for registration review.",
  },
  "APPROVED": {
    label: "Approved & Scheduled",
    description: "Your consultation request has been approved.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "Use the selected branch and schedule details for this demo record.",
  },
  "CONFIRMED": {
    label: "Confirmed",
    description: "The appointment request has a confirmed demo slot.",
    badgeStyle: "bg-green-50 text-green-950 border-green-300",
    nextAction: "Prepare any sample record details before the appointment.",
  }
};

/**
 * Returns public status information or fallback.
 */
export function getPublicStatus(status: string): PublicStatusInfo {
  const normalized = status.toUpperCase().replace(/\s+/g, "_");
  if (STATUS_MAPPINGS[normalized]) {
    return STATUS_MAPPINGS[normalized];
  }

  // Support substring checks
  for (const key of Object.keys(STATUS_MAPPINGS)) {
    if (normalized.includes(key) || key.includes(normalized)) {
      return STATUS_MAPPINGS[key];
    }
  }

  // Fallback defaults
  return {
    label: status || "Under Review",
    description: "Your transaction or ticket request is currently undergoing review.",
    badgeStyle: "bg-slate-50 text-slate-800 border-gray-300",
    nextAction: "Check back later or open a support ticket if you have additional questions.",
  };
}
