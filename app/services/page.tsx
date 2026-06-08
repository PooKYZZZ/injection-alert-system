import React from 'react';
import Link from 'next/link';
import { Search, FileSymlink, ClipboardList, Calendar, LifeBuoy, ArrowRight } from 'lucide-react';
import Container from '@/components/Container';
import Card from '@/components/Card';
import NoticeBanner from '@/components/NoticeBanner';

export default function ServicesPage() {
  const serviceList = [
    {
      title: "Land Records Search",
      category: "Public Information",
      description: "Search sample public records by record number, owner, location, or classification.",
      href: "/records/search",
      icon: Search,
    },
    {
      title: "Certified True Copy Request",
      category: "Document Certification",
      description: "Submit a request form for a sample certified copy after identifying a record.",
      href: "/records/search", // Users search first to find a record to request certified copies for! That's excellent! Or they can submit from the detail page.
      customRef: "Required: Search first",
      icon: FileSymlink,
    },
    {
      title: "Transaction & Copy Dispatch Tracking",
      category: "Status Verification",
      description: "Review the processing status of copy requests, support tickets, and appointments by reference number.",
      href: "/transactions/status",
      icon: ClipboardList,
    },
    {
      title: "Direct Appointment Scheduling",
      category: "In-Person Consultation",
      description: "Request a consultation time at a sample branch for boundary or title questions.",
      href: "/appointments",
      icon: Calendar,
    },
    {
      title: "Lodge Support Ticket & Disputes",
      category: "Citizen Grievances",
      description: "Open a support ticket to report record typos, outdated owner details, boundary questions, or system issues.",
      href: "/support",
      icon: LifeBuoy,
    },
  ];

  return (
    <Container className="space-y-8">
      {/* Breadcrumb path */}
      <div className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
        <Link href="/" className="hover:underline hover:text-slate-700">Home</Link>
        <span>/</span>
        <span className="text-slate-800">Services</span>
      </div>

      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900">Online Citizen Services Catalog</h2>
        <p className="text-slate-500 text-sm mt-1">Official registry lookup interfaces and document request workflows.</p>
      </div>

      <NoticeBanner 
        message="Important: Certified True Copy request portals require the applicant to identify the record from the public registry index first before filing a certified true copy request transaction." 
        type="info"
      />

      <div className="space-y-6">
        {serviceList.map((srv, idx) => {
          const Icon = srv.icon;
          return (
            <Card key={idx} className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 hover:border-slate-300 transition-colors">
              <div className="flex gap-4 items-start md:max-w-3xl">
                <div className="bg-slate-100 p-3 rounded-lg text-slate-700 shrink-0">
                  <Icon className="w-6 h-6" />
                </div>
                <div className="space-y-1">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
                    {srv.category}
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 pt-1">{srv.title}</h3>
                  <p className="text-slate-600 text-sm leading-relaxed">{srv.description}</p>
                </div>
              </div>
              
              <div className="shrink-0 flex flex-col items-start md:items-end gap-2">
                {srv.customRef && (
                  <span className="text-xs font-semibold text-slate-500 italic bg-amber-50 border border-amber-200 px-3 py-1 rounded">
                    {srv.customRef}
                  </span>
                )}
                <Link 
                  href={srv.href} 
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold text-xs py-2 px-4 rounded shadow-sm flex items-center gap-2 transition-colors inline-block text-center"
                >
                  <span>Select Service</span>
                  <ArrowRight className="w-3 h-3" />
                </Link>
              </div>
            </Card>
          );
        })}
      </div>
    </Container>
  );
}
