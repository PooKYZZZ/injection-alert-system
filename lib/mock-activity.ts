import { cookies } from "next/headers";

export interface MockActivity {
  referenceNo: string;
  activityType: string; // "TICKET_SUBMIT" | "APPOINTMENT_BOOK" | "COPY_REQUEST" | "DEMO_LOGIN"
  status: string;        // "PENDING_REVIEW" | "CONFIRMED" | "RELEASED" etc
  createdAt: string;
  route: string;
  method: string;
  demoTraceId?: string;
  userAgent?: string;
}

// Fixed system seeds representing compliance benchmark items
export const SEED_ACTIVITIES: MockActivity[] = [
  {
    referenceNo: "SUP-2026-0001",
    activityType: "TICKET_SUBMIT",
    status: "UNDER_PROCESSING",
    createdAt: "2026-06-03 12:00",
    route: "/support/submit",
    method: "POST",
    demoTraceId: "tr-915x-owasp-01",
    userAgent: "Mozilla/5.0 (Pentest Lab Master)",
  },
  {
    referenceNo: "APT-2026-0001",
    activityType: "APPOINTMENT_BOOK",
    status: "PENDING_REVIEW",
    createdAt: "2026-06-03 14:15",
    route: "/appointments/submit",
    method: "POST",
  },
  {
    referenceNo: "REQ-2026-0001",
    activityType: "COPY_REQUEST",
    status: "DELIVERED",
    createdAt: "2026-06-03 15:30",
    route: "/records/LND-2026-0001/request-copy",
    method: "POST",
  },
  {
    referenceNo: "TXN-2026-0001",
    activityType: "LAND_TRANSFER",
    status: "RELEASED",
    createdAt: "2026-06-03 08:32",
    route: "/records/LND-2026-0004",
    method: "GET",
  }
];

/**
 * Fetches combined mock activities (static seeds plus active session activities).
 */
export async function getMockActivities(): Promise<MockActivity[]> {
  try {
    const cookieStore = await cookies();
    const tickets = JSON.parse(cookieStore.get("user_tickets")?.value || "[]");
    const appointments = JSON.parse(cookieStore.get("user_appointments")?.value || "[]");
    const copies = JSON.parse(cookieStore.get("user_copy_requests")?.value || "[]");

    const dynamicActivities: MockActivity[] = [];

    tickets.forEach((t: any) => {
      dynamicActivities.push({
        referenceNo: t.referenceNo,
        activityType: "SUPPORT_TICKET",
        status: t.status || "PENDING_REVIEW",
        createdAt: t.timestamp,
        route: "/support/submit",
        method: "POST",
        demoTraceId: t.demoTraceId,
      });
    });

    appointments.forEach((a: any) => {
      dynamicActivities.push({
        referenceNo: a.referenceNo,
        activityType: "REGISTRAR_APPOINTMENT",
        status: a.status || "CONFIRMED",
        createdAt: a.timestamp,
        route: "/appointments/submit",
        method: "POST",
      });
    });

    copies.forEach((c: any) => {
      dynamicActivities.push({
        referenceNo: c.referenceNo,
        activityType: "CERTIFIED_COPY",
        status: c.status || "PENDING_REVIEW",
        createdAt: c.timestamp,
        route: `/records/${c.recordNo}/request-copy`,
        method: "POST",
      });
    });

    // Merge dynamic session activities with static baseline seeds
    return [...dynamicActivities, ...SEED_ACTIVITIES].sort(
      (a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  } catch (error) {
    return SEED_ACTIVITIES;
  }
}
