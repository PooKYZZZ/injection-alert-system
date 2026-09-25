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
    label: "Demo: Pending review",
    description: "This is a sample state in the demo workflow; no staff review is performed.",
    badgeStyle: "bg-amber-50 text-amber-900 border-amber-300",
    nextAction: "No action is required for this mock request.",
  },
  "UNDER_PROCESSING": {
    label: "Demo: Processing",
    description: "This is a sample processing state; no real registry review occurs.",
    badgeStyle: "bg-blue-50 text-blue-900 border-blue-300",
    nextAction: "Use the reference number to look up this demo status.",
  },
  "FOR_VERIFICATION": {
    label: "Demo: Verification",
    description: "This sample status does not verify real property coordinates.",
    badgeStyle: "bg-purple-50 text-purple-900 border-purple-300",
    nextAction: "No real verification is performed by this demo.",
  },
  "QUEUED": {
    label: "Demo: Queued",
    description: "This is a sample queue state in the mock workflow.",
    badgeStyle: "bg-slate-100 text-slate-800 border-slate-350",
    nextAction: "No document is prepared or delivered by this demo.",
  },
  "READY_FOR_PICKUP": {
    label: "Demo: Ready for pickup",
    description: "This sample status does not mean a real document is ready.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "No in-person pickup is available through this demo.",
  },
  "RELEASED": {
    label: "Demo: Released",
    description: "The demo shows a sample release status; no official packet is issued.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "No document is delivered by this demo.",
  },
  "DELIVERED": {
    label: "Demo: Delivered",
    description: "The demo shows a sample delivery status; no document is sent.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "No document is delivered by this demo.",
  },
  "REQUEST_RECEIVED": {
    label: "Demo: Request received",
    description: "The mock submission was saved for this demo workflow.",
    badgeStyle: "bg-blue-50 text-blue-950 border-blue-300",
    nextAction: "Use the reference number to look up its sample status.",
  },
  "APPROVED": {
    label: "Demo: Appointment status",
    description: "This sample status does not approve or schedule a real consultation.",
    badgeStyle: "bg-emerald-50 text-emerald-950 border-emerald-300",
    nextAction: "No meeting is booked through this demo.",
  },
  "CONFIRMED": {
    label: "Demo: Confirmed",
    description: "This mock status does not confirm a real appointment.",
    badgeStyle: "bg-green-50 text-green-950 border-green-300",
    nextAction: "No appointment is booked through this demo.",
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
    description: "This is a sample status in the demo workflow.",
    badgeStyle: "bg-slate-50 text-slate-800 border-gray-300",
    nextAction: "Use a synthetic reference number to explore the demo status page.",
  };
}
