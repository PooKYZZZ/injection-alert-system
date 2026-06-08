import React from "react";
import Link from "next/link";
import { Terminal, Shield, ArrowRight, Table, HelpCircle, CheckCircle, AlertTriangle, Layers } from "lucide-react";
import { SITE_CONFIG } from "../../lib/demo-config";

export const dynamic = "force-dynamic";

export default function DemoGuidePage() {
  const routesInventory = [
    {
      method: "GET",
      route: "/records/search",
      fields: "query",
      purpose: "Fuzzy-search registered land record indexes",
      wafRelevance: "WAF inspection cases for SQL-style local test values in search parameters against OWASP CRS Rule 942.",
      expected: "Displays filtered results or empty state if no match. Inputs are handled as text values.",
    },
    {
      method: "GET",
      route: "/records/[recordNo]",
      fields: "recordNo",
      purpose: "Retrieve exact land deed details",
      wafRelevance: "WAF inspection cases for path-style local test values on parameters; maps to CRS Rule 930/932.",
      expected: "Returns record detail or 404. Path parameter validated.",
    },
    {
      method: "GET",
      route: "/transactions/status",
      fields: "ref",
      purpose: "Track processing history via reference number",
      wafRelevance: "Reference-number inspection cases for request parameters.",
      expected: "Displays a status view from stored Prisma records or fallback seeds.",
    },
    {
      method: "POST",
      route: "/support/submit",
      fields: "email, category, subject, message, referenceNo",
      purpose: "Create support ticket with attachments references",
      wafRelevance: "WAF inspection cases for suspicious-looking local test values in fields; validates email formats; maps to CRS Rule 941.",
      expected: "Redirects (303) to /success; saves ticket in Prisma securely.",
    },
    {
      method: "POST",
      route: "/appointments/submit",
      fields: "fullName, email, branch, serviceType, preferredDate, notes",
      purpose: "Book municipal appointments",
      wafRelevance: "OWASP rule testing for boundary dates or request-format inspection.",
      expected: "Redirects (303) to /success; stores booking in Prisma and status lookup.",
    },
    {
      method: "POST",
      route: "/comments/submit",
      fields: "displayName, message",
      purpose: "Citizen feedback board posting",
      wafRelevance: "WAF inspection cases for suspicious-looking local test values in display name and message fields; maps to CRS Rule 941.",
      expected: "Redirects (303) to /comments?posted=1; stores posted content in Prisma.",
    },
    {
      method: "POST",
      route: "/login/submit",
      fields: "username, password",
      purpose: "Internal registrar credential processing",
      wafRelevance: "Login-form inspection cases for controlled local test scripts (CRS Rule 949/950).",
      expected: "Redirects (303) to /success and stores a login attempt in Prisma.",
    },
    {
      method: "GET",
      route: "/records/[recordNo]/request-copy",
      fields: "N/A",
      purpose: "Retrieve requested certified copy form",
      wafRelevance: "Inspection of standard HTTP GET request patterns.",
      expected: "Returns standalone accessible HTML form page.",
    },
    {
      method: "POST",
      route: "/records/[recordNo]/request-copy/submit",
      fields: "fullName, email, purpose, deliveryOption, remarks",
      purpose: "Order physical or digital copy of registered deeds",
      wafRelevance: "Request body inspection cases for form submissions.",
      expected: "Redirects (303) to the status page and stores a transaction in Prisma.",
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 font-sans">
      {/* Breadcrumb */}
      <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1.5 text-xs text-gray-500">
        <Link href="/" className="hover:text-slate-900 transition-colors px-1 rounded">
          Home
        </Link>
        <span aria-hidden="true">/</span>
        <span className="text-slate-900 font-medium">Demo Guide</span>
      </nav>

      {/* Hero Header */}
      <div className="mb-10 text-left">
        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-[10px] font-bold text-blue-800 uppercase tracking-wider mb-3">
          <Terminal className="h-3.5 w-3.5" aria-hidden="true" />
          WAF Test Guide
        </span>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
          WAF & CyberTrace Test Guide
        </h1>
        <p className="text-xs text-gray-500 mt-1.5 leading-relaxed max-w-4xl">
          This page documents local WAF inspection and route logging for the demo portal. It describes OWASP Core Rule Set anomaly scoring and future CyberTrace ingest flow simulation.
        </p>
      </div>

      {/* CyberTrace Flow Diagram Chart */}
      <section className="bg-slate-900 text-white rounded-xl border border-slate-800 p-8 mb-10 shadow-lg relative overflow-hidden">
        <div className="absolute inset-0 opacity-5 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:20px_20px]"></div>
        
        <div className="relative">
          <div className="flex items-center gap-2 mb-6">
            <Shield className="h-5 w-5 text-blue-400" />
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-200">
              Future CyberTrace Integration Flow
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-6 gap-4 items-center text-center text-xs relative">
            {/* Step 1 */}
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
              <span className="font-mono text-[10px] text-blue-400 font-bold block mb-1">STEP 01</span>
              <strong className="block text-white">Local Request</strong>
              <span className="text-[10px] text-slate-400 block mt-1">Citizen form post or controlled local test script</span>
            </div>

            <div className="hidden md:flex justify-center text-slate-600 font-bold font-mono">
              <ArrowRight className="h-5 w-5" />
            </div>

            {/* Step 2 */}
            <div className="bg-slate-850 border border-slate-750 rounded-lg p-4 ring-2 ring-blue-500/35">
              <span className="font-mono text-[10px] text-blue-400 font-bold block mb-1">STEP 02</span>
              <strong className="block text-white">ModSecurity + CRS</strong>
              <span className="text-[10px] text-slate-400 block mt-1">Inspects requests and applies OWASP anomaly scoring</span>
            </div>

            <div className="hidden md:flex justify-center text-slate-600 font-bold font-mono">
              <ArrowRight className="h-5 w-5" />
            </div>

            {/* Step 3 */}
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-4">
              <span className="font-mono text-[10px] text-blue-400 font-bold block mb-1">STEP 03</span>
              <strong className="block text-white text-slate-300">Demo Portal</strong>
              <span className="text-[10px] text-slate-400 block mt-1">Reads header metrics & executes safely</span>
            </div>

            <div className="hidden md:flex justify-center text-slate-600 font-bold font-mono">
              <ArrowRight className="h-5 w-5" />
            </div>

            {/* Step 4 */}
            <div className="bg-slate-850 border border-slate-750 rounded-lg p-4 md:col-span-2">
              <span className="font-mono text-[10px] text-blue-400 font-bold block mb-1">STEP 04</span>
              <strong className="block text-white">WAF Log & Ingestion</strong>
              <span className="text-[10px] text-slate-400 block mt-1">Inspection logs can route to a future CyberTrace classification flow</span>
            </div>
          </div>
        </div>
      </section>

      {/* Safety & Compliance Section */}
      <section className="bg-amber-50/50 border border-amber-200 rounded-xl p-6 mb-10">
        <h2 className="text-xs font-bold text-amber-900 uppercase tracking-widest flex items-center gap-2 mb-3">
          <AlertTriangle className="h-4 w-4 text-amber-700" />
          Simulation Lab Safety Guidelines
        </h2>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs text-amber-900 font-medium">
          <ul className="list-disc pl-5 space-y-2 leading-relaxed">
            <li><strong>Local Lab Execution Only:</strong> Never point high-volume controlled local test scripts (for example OWASP ZAP or Nikto) to public shared endpoints. Use local Docker proxies.</li>
            <li><strong>No Evasion Instruction:</strong> This guide specifies input formats and routes for testing but does not supply reverse proxy evasion syntax or bypass mechanisms.</li>
          </ul>
          <ul className="list-disc pl-5 space-y-2 leading-relaxed animate-fade-in">
            <li><strong>Output Handling:</strong> User feedback and remarks fields use standard React text rendering for displayed values.</li>
            <li><strong>Pre-Constructed Headers:</strong> Use header parameters like <code className="font-mono px-1 bg-white border border-amber-300 rounded text-slate-900">x-demo-trace-id</code> to test matching configurations.</li>
          </ul>
        </div>
      </section>

      {/* Route Inventory Table */}
      <section className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xs">
        <div className="px-6 py-4 bg-slate-50 border-b border-gray-200 flex items-center gap-1.5">
          <Table className="h-4 w-4 text-slate-700" />
          <h2 className="text-xs font-black uppercase tracking-wider text-slate-800">
            WAF Route Inventory
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-slate-50 text-[10px] uppercase font-bold text-slate-600 border-b border-gray-200 font-mono tracking-wider">
                <th className="px-6 py-4">Method</th>
                <th className="px-6 py-4">Target Route (URI)</th>
                <th className="px-6 py-4">Field Tokens</th>
                <th className="px-6 py-4">Route Purpose</th>
                <th className="px-6 py-4">OWASP CRS Relevance</th>
                <th className="px-6 py-4">Expected Outcome</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 text-xs text-slate-800">
              {routesInventory.map((item, idx) => (
                <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-block font-mono text-[10px] font-bold px-2 py-0.5 rounded ${
                      item.method === "POST" ? "bg-blue-50 text-blue-800 border border-blue-200" : "bg-emerald-50 text-emerald-800 border border-emerald-200"
                    }`}>
                      {item.method}
                    </span>
                  </td>
                  <td className="px-6 py-4 font-mono font-bold text-slate-900 whitespace-nowrap">
                    {item.route}
                  </td>
                  <td className="px-6 py-4 font-mono text-[11px] text-slate-500 whitespace-nowrap">
                    {item.fields}
                  </td>
                  <td className="px-6 py-4 text-slate-600">
                    {item.purpose}
                  </td>
                  <td className="px-6 py-4 text-blue-950 font-medium">
                    {item.wafRelevance}
                  </td>
                  <td className="px-6 py-4 text-slate-500">
                    {item.expected}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Guide Footer */}
      <div className="mt-8 text-center text-xs text-gray-400">
        Use local request tools only in a controlled environment.
      </div>
    </div>
  );
}
