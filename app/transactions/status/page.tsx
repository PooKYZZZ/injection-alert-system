import React from "react";
import Link from "next/link";
import type { Appointment, SupportTicket, Transaction } from "@prisma/client";
import { 
  Search, 
  ShieldCheck, 
  Clock, 
  Ticket, 
  FileText, 
  CalendarDays, 
  History, 
  ArrowRight
} from "lucide-react";
import { SITE_CONFIG } from "../../../lib/demo-config";
import { getPublicStatus } from "../../../lib/status";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

interface SearchParams {
  ref?: string;
}

interface StatusDisplayItem {
  referenceNo: string;
  type: string;
  title: string;
  subText: string;
  status: string;
  timestamp: string;
}

interface RecentSubmission {
  ref: string;
  type: string;
  label: string;
  date: string;
}

export default async function TransactionStatusPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const { ref } = await searchParams;
  const uppercaseRef = (ref || "").toUpperCase().trim();

  // Query Prisma for support tickets, appointments, and transactions
  const [supportTicket, appointment, transaction] = await Promise.all([
    uppercaseRef ? prisma.supportTicket.findFirst({ where: { referenceNo: uppercaseRef } }) : null,
    uppercaseRef ? prisma.appointment.findUnique({ where: { referenceNo: uppercaseRef } }) : null,
    uppercaseRef ? prisma.transaction.findUnique({ where: { referenceNo: uppercaseRef } }) : null,
  ]);

  // Map Prisma results to display format
  const match: StatusDisplayItem | null = supportTicket
    ? {
        referenceNo: supportTicket.referenceNo ?? "",
        type: "Support Ticket",
        title: supportTicket.subject,
        subText: `Category: ${supportTicket.category}`,
        status: supportTicket.status,
        timestamp: supportTicket.createdAt?.toISOString().replace("T", " ").substring(0, 16) || "",
      }
    : appointment
    ? {
        referenceNo: appointment.referenceNo,
        type: "Registrar Appointment",
        title: `Office consultation for ${appointment.fullName}`,
        subText: `Branch: ${appointment.branch} • Service: ${appointment.serviceType}`,
        status: appointment.status,
        timestamp: appointment.createdAt?.toISOString().replace("T", " ").substring(0, 16) || "",
      }
    : transaction
    ? {
        referenceNo: transaction.referenceNo,
        type: "Certified Deed Request",
        title: `Copy Request for Deed ${transaction.recordNo}`,
        subText: `Recipient: ${transaction.applicantName} • Delivery: ${transaction.deliveryOption}`,
        status: transaction.status,
        timestamp: transaction.createdAt?.toISOString().replace("T", " ").substring(0, 16) || "",
      }
    : null;

  // Seed static items for demo purposes
  const INITIAL_DEMO_ITEMS: Record<string, StatusDisplayItem> = {
    "SUP-2026-0001": {
      referenceNo: "SUP-2026-0001",
      type: "Support Ticket",
      title: "Overlapping land plot mapping query",
      subText: "Category: Cadastral Index Mapping",
      status: "UNDER_PROCESSING",
      timestamp: "2026-06-03 12:00",
    },
    "APT-2026-0001": {
      referenceNo: "APT-2026-0001",
      type: "Registrar Appointment",
      title: "Boundary arbitration session",
      subText: "Branch: North District Registry • Service: Dispute Arbitration",
      status: "PENDING_REVIEW",
      timestamp: "2026-06-03 14:15",
    },
    "REQ-2026-0001": {
      referenceNo: "REQ-2026-0001",
      type: "Certified Deed Request",
      title: "Deed Copy Request for LND-2026-0001",
      subText: "Recipient: Demo Resident A • Option: Digital copy",
      status: "DELIVERED",
      timestamp: "2026-06-03 15:30",
    },
    "TXN-2026-0001": {
      referenceNo: "TXN-2026-0001",
      type: "Transaction Ledger Reference",
      title: "Title Deed Transfer - LND-2026-0004",
      subText: "Status: Finalized Ledger Append",
      status: "RELEASED",
      timestamp: "2026-06-03 08:32",
    },
  };

  // Combine seed and Prisma results
  const displayMatch: StatusDisplayItem | null = match || (uppercaseRef ? INITIAL_DEMO_ITEMS[uppercaseRef] ?? null : null);

  // Fetch recent submissions from Prisma for session list
  const recentSupportTickets: SupportTicket[] = await prisma.supportTicket.findMany({ orderBy: { createdAt: "desc" }, take: 10 });
  const recentAppointments: Appointment[] = await prisma.appointment.findMany({ orderBy: { createdAt: "desc" }, take: 10 });
  const recentTransactions: Transaction[] = await prisma.transaction.findMany({ orderBy: { createdAt: "desc" }, take: 10 });

  const totalUserSubmissions: RecentSubmission[] = [
    ...recentSupportTickets.map((t) => ({ ref: t.referenceNo ?? "", type: "SUPPORT", label: t.subject, date: t.createdAt?.toISOString().substring(0, 16).replace("T", " ") || "" })),
    ...recentAppointments.map((a) => ({ ref: a.referenceNo, type: "APPOINTMENT", label: `Meeting for ${a.fullName}`, date: a.createdAt?.toISOString().substring(0, 16).replace("T", " ") || "" })),
    ...recentTransactions.map((c) => ({ ref: c.referenceNo, type: "COPY", label: `Deed Copy: ${c.recordNo}`, date: c.createdAt?.toISOString().substring(0, 16).replace("T", " ") || "" })),
  ];

  // Map progress bar width
  const getTimelineProgress = (status: string) => {
    const s = status.toUpperCase();
    if (s.includes("RECEIVED") || s.includes("TICKET")) return "w-1/4";
    if (s.includes("REVIEW") || s.includes("PENDING")) return "w-1/2";
    if (s.includes("PROCESSING") || s.includes("VERIFICATION") || s.includes("CONFIRMED")) return "w-3/4";
    if (s.includes("DELIVERED") || s.includes("RELEASED") || s.includes("PICKUP")) return "w-full";
    return "w-1/3";
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 font-sans">
      {/* Breadcrumbs */}
      <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1.5 text-xs text-gray-500">
        <Link href="/" className="hover:text-slate-900 transition-colors focus:ring-1 focus:ring-blue-500 px-1 rounded">
          Home
        </Link>
        <span aria-hidden="true">/</span>
        <span className="text-slate-900 font-medium">Track Status</span>
      </nav>

      {/* Header section */}
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
          Registry Status Tracking Desk
        </h1>
        <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
          Perform digital status inquiries on pending cadastral requests, support tickets, and scheduling codes. Mapped against formal public status models.
        </p>
      </div>

      {/* Lookup search bar */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs mb-8">
        <form id="status-search-form" action="/transactions/status" method="get" className="space-y-4">
          <div>
            <label htmlFor="status-ref-input" className="block text-[11px] font-bold text-slate-600 uppercase tracking-wider mb-2">
              Enter reference number <span className="text-red-600" aria-hidden="true">*</span>
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="flex-1 relative focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-1 rounded-lg">
                <input
                  id="status-ref-input"
                  type="text"
                  name="ref"
                  defaultValue={ref || ""}
                  placeholder="e.g., SUP-2026-0001, APT-2026-[xxxx]..."
                  required
                  className="w-full bg-white border border-gray-300 rounded-lg pl-10 pr-3 py-2.5 text-xs focus:outline-hidden font-mono uppercase tracking-wider text-slate-800"
                />
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center text-gray-400 pointer-events-none" aria-hidden="true">
                  <Search className="h-4 w-4" />
                </div>
              </div>
              <button
                id="status-lookup-btn"
                type="submit"
                className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs px-6 py-2.5 rounded-lg shadow-xs transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 font-sans min-h-[44px]"
              >
                Query Transaction
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* Search Result view */}
      {uppercaseRef ? (
        displayMatch ? (
          (() => {
            const statusInfo = getPublicStatus(displayMatch.status);
            return (
              <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm mb-8">
                {/* Result Header */}
                <div className="bg-slate-900 text-white px-6 py-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-[9px] uppercase font-bold tracking-wider text-slate-400 font-mono">
{displayMatch.type}
                       </span>
                       <h3 className="font-mono text-base font-extrabold tracking-wide mt-0.5">
                         {displayMatch.referenceNo}
                       </h3>
                     </div>
                     <span className={`px-2.5 py-1 rounded text-[10px] font-bold font-mono tracking-wider border self-start sm:self-auto ${statusInfo.badgeStyle}`}>
                       {statusInfo.label}
                  </span>
                </div>

                <div className="p-6 space-y-6">
                  {/* Central Status Card */}
                  <div className="bg-slate-50 border border-gray-200 rounded-lg p-5">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                      Registry Status Explanation
                    </h4>
                    <p className="text-xs text-gray-600 leading-relaxed mt-2">
                      {statusInfo.description}
                    </p>
                  </div>

                  {/* Progress / Timeline Indicator */}
                  <div>
                    <div className="grid grid-cols-2 gap-2 sm:flex sm:justify-between sm:items-center text-[10px] uppercase font-bold text-gray-400 tracking-wider mb-2">
                      <span>Submitted</span>
                      <span>Reviewing</span>
                      <span>Under Processing</span>
                      <span>Dispatched / Done</span>
                    </div>
                    <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden relative border border-gray-200">
                      <div className={`h-full bg-blue-600 rounded-full transition-all duration-500 ${getTimelineProgress(displayMatch.status)}`}></div>
                    </div>
                  </div>

                  {/* Context block */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-4 border-t border-gray-100">
                    <div>
                      <h4 className="text-[10px] uppercase font-mono font-bold text-gray-400 tracking-wider">Subject Summary</h4>
<p className="text-xs font-bold text-slate-900 mt-1">{displayMatch.title}</p>
                       <p className="text-[11px] text-gray-500 mt-0.5">{displayMatch.subText}</p>
                    </div>
                    <div>
                      <h4 className="text-[10px] uppercase font-mono font-bold text-gray-400 tracking-wider">Citizen Next Action Guidelines</h4>
                      <p className="text-xs text-blue-900 font-medium bg-blue-50 border border-blue-100 p-2.5 rounded-lg mt-1 select-none">
                        {statusInfo.nextAction}
                      </p>
                    </div>
                  </div>

                  {/* Demo notice */}
                  <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex gap-2.5">
                    <ShieldCheck className="h-4 w-4 text-amber-700 shrink-0 mt-0.5" aria-hidden="true" />
                    <div className="text-[10px] text-amber-800 leading-relaxed font-sans">
                      <span className="font-bold text-amber-900 block" id="simulation-status-notice">Demo Notice</span>
                      This is a demo portal. All records, submissions, and reference numbers are mock data for local testing only.
                    </div>
                  </div>
                </div>
              </div>
            );
          })()
        ) : (
          <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center mb-8">
            <Search className="h-8 w-8 text-red-500 mx-auto mb-3" aria-hidden="true" />
            <h2 className="text-sm font-bold text-slate-900">Reference code not found</h2>
            <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto leading-relaxed">
              We couldn&apos;t locate reference &ldquo;{ref}&rdquo; in the current session or the seeded demo entries below. Use one of the entries below to inspect how statuses render.
            </p>
          </div>
        )
      ) : (
        /* Empty State */
        <div className="bg-slate-50 border border-dashed border-gray-300 rounded-xl p-10 text-center mb-8">
          <Clock className="h-8 w-8 text-slate-400 mx-auto mb-3" />
          <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">Ready for Registry Status Inquiry</h3>
          <p className="text-xs text-gray-500 mt-1 max-w-sm mx-auto leading-relaxed">
            Submit any record, ticket, or appointment booking to generate a reference number (e.g., <code className="font-mono bg-white px-1">SUP-2026-0001</code>) then search above.
          </p>
        </div>
      )}

      {/* Historical activities logging and tracker seeds */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left column: Session transaction logs */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xs">
            <div className="px-6 py-4 bg-slate-50 border-b border-gray-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <History className="h-4 w-4 text-slate-700" aria-hidden="true" />
                <h2 className="text-xs font-black tracking-wider uppercase text-slate-800">
                  Transactions From Current Session
                </h2>
              </div>
              <span className="text-[10px] text-gray-400 font-mono">
                {totalUserSubmissions.length} Registered
              </span>
            </div>

            <div className="divide-y divide-gray-100">
              {totalUserSubmissions.length > 0 ? (
                totalUserSubmissions.map((item, index) => (
                  <div key={index} className="p-4 sm:px-6 flex flex-col sm:flex-row sm:items-center sm:justify-between hover:bg-slate-50/50 transition-colors gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 border border-blue-100 px-2 py-0.5 rounded">
                          {item.ref}
                        </span>
                        <span className="text-[9px] uppercase font-mono font-bold px-1.5 py-0.5 bg-slate-100 border text-slate-500 rounded-full">
                          {item.type}
                        </span>
                      </div>
                      <p className="text-xs font-semibold text-slate-850 max-w-xs">{item.label}</p>
                    </div>
                    <div className="text-left sm:text-right shrink-0">
                      <span className="block text-[10px] text-gray-400 font-mono">{item.date}</span>
                      <Link
                        href={`/transactions/status?ref=${item.ref}`}
                        className="text-[10px] font-bold text-blue-600 hover:underline inline-block mt-0.5"
                      >
                        Track Status
                      </Link>
                    </div>
                  </div>
                ))
              ) : (
                <div className="p-8 text-center text-gray-400 text-xs leading-relaxed">
                  No active transaction submissions are registered in your current browser session. Fill out Support, Appointments, or Certified copy forms to generate entries.
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right column: sample references and general info */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-xs">
            <h3 className="text-xs font-black uppercase tracking-wider text-slate-800 mb-2">
              Sample Reference List
            </h3>
            <p className="text-xs text-gray-500 leading-relaxed mb-4">
              Select a sample reference to see how status labels map to progress states.
            </p>

            <div className="space-y-2">
              {Object.keys(INITIAL_DEMO_ITEMS).map((seedKey) => {
                const seedObj = INITIAL_DEMO_ITEMS[seedKey];
                const statusInfo = getPublicStatus(seedObj.status);
                return (
                  <Link
                    key={seedKey}
                    href={`/transactions/status?ref=${seedKey}`}
                    className="flex flex-col p-3 bg-slate-50 hover:bg-slate-100 rounded-lg border border-gray-200 transition-colors text-left"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-xs font-bold text-slate-900">{seedKey}</span>
                      <span className={`px-1.5 py-0.2 rounded text-[8px] font-bold font-mono tracking-wider border ${statusInfo.badgeStyle}`}>
                        {statusInfo.label}
                      </span>
                    </div>
                    <span className="text-[10px] text-gray-400 mt-1">{seedObj.title}</span>
                  </Link>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
