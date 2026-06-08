import React from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import { MOCK_RECORDS } from "../../../lib/db";
import { Landmark, FileText, ArrowLeft, ShieldCheck, MapPin, Layers, LayoutGrid, Eye, ArrowRight } from "lucide-react";
import { SITE_CONFIG } from "../../../lib/demo-config";

export const dynamic = "force-dynamic";

interface RouteParams {
  recordNo: string;
}

export default async function RecordDetailPage({
  params,
}: {
  params: Promise<RouteParams>;
}) {
  const { recordNo } = await params;
  const record = MOCK_RECORDS.find(
    (r) => r.recordNo.toUpperCase() === recordNo.toUpperCase()
  );

  if (!record) {
    notFound();
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10 font-sans">
      {/* Back link */}
      <div className="mb-6">
        <Link
          href="/records/search"
          className="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-slate-900 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1.5 py-0.5 font-sans"
        >
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
          Return to search results
        </Link>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 shadow-xs divide-y divide-gray-100 overflow-hidden">
        {/* Detail Header Banner */}
        <div className="p-6 sm:p-8 bg-slate-50 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-slate-200/80 border border-slate-300 font-mono text-[9px] font-bold text-slate-800 mb-2 uppercase">
              <Landmark className="h-3.5 w-3.5 text-slate-700" aria-hidden="true" />
              Public Deed Statement
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 font-mono">
              {record.recordNo}
            </h1>
            <p className="text-xs text-gray-500 flex items-center gap-1 mt-1 leading-relaxed">
              <MapPin className="h-3.5 w-3.5 text-gray-400 shrink-0" aria-hidden="true" />
              {record.location}
            </p>
          </div>

          <div>
            <Link
              id="request-certified-copy-btn"
              href={`/records/${record.recordNo}/request-copy`}
              className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs px-4 py-2.5 rounded-lg shadow-xs cursor-pointer transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 min-h-[44px]"
            >
              <FileText className="h-4 w-4" aria-hidden="true" />
              Request Certified Copy
            </Link>
          </div>
        </div>

        {/* Structured Info Architecture */}
        <div className="p-6 sm:p-8 grid grid-cols-1 md:grid-cols-2 gap-8 bg-white">
          
          {/* Section 1: Record Overview */}
          <div className="space-y-6">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-2">
              <LayoutGrid className="h-4 w-4 text-slate-700" />
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-widest">
                Deed Profile Overview
              </h2>
            </div>
            
            <div className="space-y-4">
              <div>
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Registered Deed Owner
                </h3>
                <p className="text-xs font-bold text-slate-900 mt-1">{record.owner}</p>
              </div>

              <div>
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Property Dimensions
                </h3>
                <p className="text-xs font-mono font-medium text-slate-800 mt-0.5">{record.size}</p>
              </div>

              <div>
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Official Land Classification
                </h3>
                <p className="text-xs text-slate-700 mt-1">{record.classification}</p>
              </div>
            </div>
          </div>

          {/* Section 2: Location & Survey details */}
          <div className="space-y-6">
            <div className="flex items-center gap-2 border-b border-gray-100 pb-2">
              <Layers className="h-4 w-4 text-slate-700" />
              <h2 className="text-xs font-bold text-slate-800 uppercase tracking-widest">
                Location & Processing Status
              </h2>
            </div>

            <div className="space-y-4">
              <div>
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Cadastral Survey Date
                </h3>
                <p className="text-xs font-mono text-slate-700 mt-0.5">{record.surveyDate}</p>
              </div>

              <div>
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Current Legal Status
                </h3>
                <div className="mt-1">
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                    {record.status}
                  </span>
                </div>
              </div>

              <div>
                <h3 className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  Authorized Registry Node
                </h3>
                <p className="text-xs text-slate-600 mt-1">
                  National Cadastre Office (Region Delta Outpost Branch)
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Section 3: Available Actions Box */}
        <div className="p-6 sm:p-8 bg-slate-50/50">
          <h2 className="text-xs font-bold text-slate-800 uppercase tracking-wider mb-4 flex items-center gap-1.5 border-b border-slate-100 pb-2">
            <Eye className="h-4 w-4 text-slate-700" />
            Registry Management Actions
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="bg-white p-4 rounded-lg border border-gray-200 hover:border-slate-350 transition-colors">
              <h3 className="text-xs font-bold text-slate-900 mb-1">Request certified soft copy</h3>
              <p className="text-[11px] text-gray-400 mb-3 leading-relaxed">
                Receive a demo copy summary for this sample record.
              </p>
              <Link
                href={`/records/${record.recordNo}/request-copy`}
                className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                Start request <ArrowRight className="h-3 w-3" />
              </Link>
            </div>

            <div className="bg-white p-4 rounded-lg border border-gray-200 hover:border-slate-350 transition-colors">
              <h3 className="text-xs font-bold text-slate-900 mb-1">Schedule registry consultation</h3>
              <p className="text-[11px] text-gray-400 mb-3 leading-relaxed">
                Book a consultation or arbitration ticket with surveyors concerning this property.
              </p>
              <Link
                href="/appointments"
                className="text-xs font-bold text-blue-600 hover:text-blue-800 flex items-center gap-1"
              >
                Book online session <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </div>
        </div>

        {/* Demo notice banner */}
        <div className="p-6 sm:p-8 bg-amber-50/20 flex flex-col sm:flex-row items-center gap-4">
          <div className="p-3 bg-white rounded-lg border border-amber-200 text-amber-700 shrink-0" aria-hidden="true">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-xs font-bold text-amber-900 uppercase tracking-wider">
              Demo Notice
            </h2>
            <p className="text-[10px] text-amber-800 mt-1 leading-relaxed">
              This is a demo portal. All records, submissions, and reference numbers are mock data for local testing only.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
