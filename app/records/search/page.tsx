import React from "react";
import Link from "next/link";
import { headers } from "next/headers";
import { MOCK_RECORDS } from "../../../lib/db";
import { Search, Map, ArrowRight, Layers, FileSpreadsheet } from "lucide-react";
import { SITE_CONFIG } from "../../../lib/demo-config";
import { EnforcementChallenge } from "../../../components/EnforcementChallenge";
import {
  checkRecordSearchEnforcementFromRuntime,
  enforcementRuntimeConfig,
} from "../../../lib/enforcement-check-runtime";
import { applicationBlockAppliedLogEvent } from "../../../lib/enforcement-check";
import { runRecordSearchProtectedWork } from "./record-search-protection";
import { recordPr7PortalStage } from "../../../lib/pr7-portal-sentinel";

export const dynamic = "force-dynamic";

interface SearchParams {
  query?: string;
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const evidenceId = (await headers()).get("x-pr7-evidence-id");
  await recordPr7PortalStage({
    evidenceId,
    stage: "request_received",
  });
  const enforcement = await checkRecordSearchEnforcementFromRuntime();
  const protectedSearch = await runRecordSearchProtectedWork(
    enforcement,
    async () => {
      await recordPr7PortalStage({
        evidenceId,
        stage: "protected_work_started",
      });
      const { query } = await searchParams;
      const lowercaseQuery = (query || "").toLowerCase().trim();
      const results = MOCK_RECORDS.filter((record) => {
        if (!lowercaseQuery) return true;
        return (
          record.recordNo.toLowerCase().includes(lowercaseQuery) ||
          record.owner.toLowerCase().includes(lowercaseQuery) ||
          record.location.toLowerCase().includes(lowercaseQuery) ||
          record.classification.toLowerCase().includes(lowercaseQuery)
        );
      });
      return { query, lowercaseQuery, results };
    },
  );
  if (enforcement.decision === "BLOCK") {
    console.info(JSON.stringify(applicationBlockAppliedLogEvent()));
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center font-sans">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
          Access temporarily blocked
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Access to this request is temporarily blocked.
        </p>
      </div>
    );
  }
  if (enforcement.decision === "CHALLENGE") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center font-sans">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
          Verification required
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Complete the security verification before searching the public land-record index.
        </p>
        <div className="mt-8 rounded-xl border border-slate-200 bg-white p-6 text-left shadow-xs">
          <EnforcementChallenge siteKey={enforcementRuntimeConfig().siteKey || ""} />
        </div>
      </div>
    );
  }
  if (enforcement.decision === "THROTTLE") {
    return (
      <div className="mx-auto max-w-2xl px-4 py-20 text-center font-sans">
        <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">
          Search temporarily limited
        </h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          Please wait {enforcement.retryAfterSeconds} seconds before trying again.
        </p>
      </div>
    );
  }
  if (protectedSearch === null) {
    throw new Error("Record search work was not available after an ALLOW decision");
  }
  const { query, lowercaseQuery, results } = protectedSearch;

  const getStatusBadgeClass = (status: string) => {
    const s = status.toLowerCase();
    if (s.includes("active") || s.includes("registered")) {
      return "bg-emerald-50 text-emerald-800 border-emerald-200";
    }
    if (s.includes("review") || s.includes("dispute")) {
      return "bg-amber-50 text-amber-800 border-amber-200";
    }
    if (s.includes("collateral") || s.includes("mortgage")) {
      return "bg-purple-50 text-purple-800 border-purple-200";
    }
    if (s.includes("preserve") || s.includes("historical")) {
      return "bg-slate-50 text-slate-800 border-slate-200";
    }
    return "bg-slate-50 text-slate-800 border-slate-200";
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 font-sans">
      {/* Breadcrumbs */}
      <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1.5 text-xs text-gray-500">
        <Link href="/" className="hover:text-slate-900 transition-colors focus:ring-1 focus:ring-blue-500 rounded px-1">
          Home
        </Link>
        <span aria-hidden="true">/</span>
        <span className="text-slate-900 font-medium font-sans">Search Records</span>
      </nav>

      {/* Header segment */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 mb-8">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">
            Search Land Deed Registers
          </h1>
          <p className="text-xs text-gray-500 mt-1.5">
            Query public cadastral registers, parcel boundaries, and authorized title deeds under governance indexes.
          </p>
        </div>

        {/* Inline Search Bar */}
        <form
          id="search-inline-form"
          action="/records/search"
          method="get"
          className="flex-1 max-w-md bg-white border border-gray-300 rounded-lg p-1.5 flex gap-2 shadow-xs focus-within:ring-2 focus-within:ring-blue-500 focus-within:ring-offset-1"
        >
          <label htmlFor="search-inline-query" className="sr-only">Search records by record number or owner name</label>
          <input
            id="search-inline-query"
            type="text"
            name="query"
            defaultValue={query || ""}
            placeholder="Search record no. or owner name..."
            className="w-full bg-transparent px-2.5 text-xs focus:outline-hidden placeholder-gray-400 font-sans text-slate-800"
          />
          <button
            id="search-inline-submit"
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2 rounded-md transition-colors cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            Search
          </button>
        </form>
      </div>

      {/* active filters bar and record counts */}
      <div className="mb-6 bg-slate-50 border border-gray-200 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2 text-slate-700">
          <FileSpreadsheet className="h-4 w-4 text-slate-500 shrink-0" />
          <span>
            Database Registry Size: <strong className="font-semibold text-slate-900">{MOCK_RECORDS.length} total</strong> indexes
          </span>
          {lowercaseQuery && (
            <>
              <span className="text-gray-300">|</span>
              <span className="text-slate-600">
                Active filter parameter: <mark className="bg-amber-100 text-slate-800 px-1 py-0.5 rounded font-mono text-[11px] font-semibold">&ldquo;{query}&rdquo;</mark>
              </span>
            </>
          )}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-slate-500 font-mono text-[11px]">
            Showing <strong className="font-semibold text-slate-900">{results.length}</strong> index records
          </span>
          {lowercaseQuery && (
            <Link
              href="/records/search"
              className="text-xs font-bold text-red-600 hover:text-red-800 hover:underline focus:outline-none"
            >
              Clear current filters
            </Link>
          )}
        </div>
      </div>

      {/* Main Results Listing */}
      <div className="grid grid-cols-1 gap-6">
        {results.length > 0 ? (
          <div className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-xs">
            <div className="overflow-x-auto" data-table-scroll>
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 border-b border-gray-200 text-[10px] font-bold text-slate-700 uppercase tracking-wider font-mono">
                    <th className="px-6 py-4">Deed Reference No.</th>
                    <th className="px-6 py-4">Title Owner</th>
                    <th className="px-6 py-4">Property Location</th>
                    <th className="px-6 py-4">Area Dimension</th>
                    <th className="px-6 py-4">Legal Classification</th>
                    <th className="px-6 py-4">Deed Status</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-xs text-slate-800">
                  {results.map((record) => (
                    <tr key={record.recordNo} className="hover:bg-slate-50/50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link
                          href={`/records/${record.recordNo}`}
                          className="font-mono font-bold text-blue-600 hover:text-blue-850 hover:underline py-0.5 px-1.5 rounded bg-blue-50/50 border border-blue-100/50"
                        >
                          {record.recordNo}
                        </Link>
                      </td>
                      <td className="px-6 py-4 font-bold">
                        {record.owner}
                      </td>
                      <td className="px-6 py-4 text-gray-500 max-w-xs">
                        {record.location}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap font-mono text-gray-700">
                        {record.size}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-gray-500">
                        {record.classification}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${getStatusBadgeClass(record.status)}`}>
                          {record.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right">
                        <Link
                          href={`/records/${record.recordNo}`}
                          className="inline-flex items-center gap-1 font-bold text-xs text-slate-900 hover:text-blue-600 transition-colors group"
                          aria-label={`View details for ${record.recordNo}`}
                        >
                          View Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-slate-50 border border-dashed border-gray-300 rounded-xl p-12 text-center">
            <Layers className="h-10 w-10 text-gray-400 mx-auto mb-4" />
            <h3 className="text-sm font-bold text-slate-900">No matching indexes found</h3>
            <p className="text-xs text-gray-500 mt-1 max-w-xs mx-auto leading-relaxed">
              We couldn&apos;t locate any records matching your search query &ldquo;{query}&rdquo;. Please modify query parameters or reset your filters.
            </p>
            <Link
              href="/records/search"
              className="mt-4 inline-flex px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-semibold h-10 items-center justify-center transition-colors"
            >
              Reset Filters
            </Link>
          </div>
        )}
      </div>

      {/* Cadastral Helper Section */}
      <div className="mt-10 grid grid-cols-1 md:grid-cols-2 gap-6 bg-slate-50 rounded-2xl border border-gray-200 p-6">
        <div>
          <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Map className="h-4 w-4 text-slate-700" aria-hidden="true" />
            Registry Mapping Guidance
          </h2>
          <p className="text-xs text-slate-500 mt-2 leading-relaxed">
            All records displayed are public index files. If you require absolute boundary validation or custom cadastral coordinates map printouts, please request a certified digital copy or register an appointment with the local Municipal Registrar.
          </p>
        </div>
        <div className="flex flex-col md:items-end justify-center">
          <Link
            href="/appointments"
            className="px-4 py-2 border border-slate-950 text-slate-950 hover:bg-slate-950 hover:text-white rounded-lg text-xs font-bold transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[44px] flex items-center justify-center"
          >
            Schedule Office Appointment
          </Link>
        </div>
      </div>
    </div>
  );
}
