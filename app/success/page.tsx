import React from "react";
import Link from "next/link";
import { CheckCircle2, ArrowRight, ShieldCheck, Ticket, CalendarDays, FileText, MessageSquare } from "lucide-react";

export const dynamic = "force-dynamic";

interface SuccessParams {
  type?: string;
  ref?: string;
}

export default async function SuccessPage({
  searchParams,
}: {
  searchParams: Promise<SuccessParams>;
}) {
  const { type, ref } = await searchParams;

  let title = "Submission Received";
  let description = "Your demo request was recorded.";
  let badgeText = "RECEIVED";
  let contentMessage = "";
  let requestType = "General request";
  let disclaimer = "CyberTrace test demo. Use synthetic values only; do not enter real personal or property details.";
  let linkHref = "/";
  let linkText = "Return to Dashboard";
  let IconComponent = CheckCircle2;

  if (type === "support") {
    title = "Demo support request received";
    description = "Your mock ticket was saved. No email reply is sent.";
    badgeText = "DEMO SUPPORT";
    requestType = "Support request";
    contentMessage = "Use the reference number below to look up this demo request's status.";
    linkHref = "/support";
    linkText = "Send another demo request";
    IconComponent = Ticket;
  } else if (type === "appointment") {
    title = "Demo appointment request received";
    description = "Your test request was recorded. It does not book a real appointment or send email.";
    badgeText = "DEMO REQUEST";
    requestType = "Appointment request";
    contentMessage = "This page confirms a test request only. No real appointment was booked.";
    linkHref = "/appointments";
    linkText = "Send another demo request";
    IconComponent = CalendarDays;
  } else if (type === "copy") {
    title = "Sample copy request received";
    description = "Your mock request was recorded. No certified document is produced or delivered.";
    badgeText = "SAMPLE COPY";
    requestType = "Sample copy request";
    contentMessage = "This demo records a sample copy request only.";
    linkHref = `/records/search`;
    linkText = "Return to sample records";
    IconComponent = FileText;
  } else if (type === "comment") {
    title = "Comment added to the demo";
    description = "Your mock comment was saved to the demo feedback page.";
    badgeText = "DEMO COMMENT";
    requestType = "Comment";
    contentMessage = "Comments may be visible to other users of this demo. Do not include personal details.";
    linkHref = "/";
    linkText = "Return to demo home";
    IconComponent = MessageSquare;
  } else if (type === "login") {
    title = "Demo login attempt recorded";
    description = "Authentication is disabled. No account or session was created.";
    badgeText = "DEMO LOGIN";
    requestType = "Demo login attempt";
    contentMessage = "The test attempt was recorded. No password is stored and no sign-in occurred.";
    disclaimer = "This demo does not create accounts or sessions. Use synthetic login values only.";
    linkHref = "/";
    linkText = "Return to demo portal";
    IconComponent = ShieldCheck;
  }

  return (
    <section className="max-w-xl mx-auto px-4 sm:px-6 lg:px-8 py-16 font-sans">
      <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden shadow-md">
        {/* Banner */}
        <div className="bg-slate-50 border-b border-gray-100 p-8 text-center flex flex-col items-center">
          <div className="h-14 w-14 bg-blue-600 text-white flex items-center justify-center rounded-2xl shadow-md mb-4" aria-hidden="true">
            <IconComponent className="h-7 w-7" />
          </div>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[9px] font-mono font-bold uppercase tracking-wider bg-slate-200/80 text-slate-800 border border-slate-300">
            {badgeText}
          </span>
          <h1 className="text-2xl font-black tracking-tight text-slate-900 mt-3 font-sans">
            {title}
          </h1>
          <p className="text-xs text-slate-500 mt-1 max-w-sm leading-relaxed">
            {description}
          </p>
        </div>

        {/* Dynamic Detail Card content */}
        <div className="p-8 space-y-6">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="bg-slate-50 border border-gray-200 rounded-lg p-3">
              <dt className="font-bold uppercase tracking-wider text-slate-500 text-[10px]">Request type</dt>
              <dd className="mt-1 text-slate-900 font-semibold">{requestType}</dd>
            </div>
            <div className="bg-slate-50 border border-gray-200 rounded-lg p-3">
              <dt className="font-bold uppercase tracking-wider text-slate-500 text-[10px]">Status</dt>
              <dd className="mt-1 text-slate-900 font-semibold">Request Received</dd>
            </div>
          </dl>

          {ref && (
            <div className="bg-slate-900 text-white rounded-xl p-5 border border-slate-800 flex items-center justify-between shadow-inner">
              <div>
                <span className="block text-[9px] uppercase tracking-wider text-slate-400 font-mono">
                  Assigned Reference number
                </span>
                <span className="font-mono text-lg font-extrabold tracking-wider mt-0.5 block selection:bg-slate-700">
                  {ref}
                </span>
              </div>
              <div className="text-[10px] text-emerald-400 font-mono select-none px-2 py-1 rounded bg-slate-800 border border-slate-700">
                DEMO
              </div>
            </div>
          )}

          <div className="bg-slate-50 border border-gray-200 rounded-xl p-5 text-xs text-slate-700 leading-relaxed">
            {contentMessage}
          </div>

          {/* Demo notice indicator */}
          <div className="border border-dashed border-gray-350 rounded-xl p-5 bg-amber-50/20 flex gap-3">
            <ShieldCheck className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" aria-hidden="true" />
            <div>
              <h2 className="font-bold text-[10px] text-amber-900 uppercase tracking-wider">
                Demo Notice
              </h2>
              <p className="text-[10px] text-amber-800 mt-1 leading-relaxed">
                {disclaimer}
              </p>
            </div>
          </div>

          <div className="pt-4 border-t border-gray-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            <Link
              href="/transactions/status"
              className="text-xs font-semibold text-gray-500 hover:text-slate-900 transition-colors flex items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1.5"
            >
              Track transaction status
            </Link>

            <Link
              id="success-redirect-back-link"
              href={linkHref}
              aria-label={`Next action: ${linkText}`}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-1 bg-blue-600 hover:bg-blue-700 transition-colors text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-sm group cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 h-11"
            >
              {linkText}
              <ArrowRight className="h-3.5 w-3.5 transform group-hover:translate-x-0.5 transition-transform" aria-hidden="true" />
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
