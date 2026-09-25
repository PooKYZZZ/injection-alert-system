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
      title: "Sample Copy Request",
      category: "Mock document request",
      description: "Create a mock copy request for a sample record. No certified document is issued.",
      href: "/records/search", // Users search first to find a record to request certified copies for! That's excellent! Or they can submit from the detail page.
      customRef: "Required: Search first",
      icon: FileSymlink,
    },
    {
      title: "Demo Request Status",
      category: "Sample status lookup",
      description: "Look up sample statuses for mock requests by reference number. Updates are not live.",
      href: "/transactions/status",
      icon: ClipboardList,
    },
    {
      title: "Appointment Request Form",
      category: "Mock form",
      description: "Submit a mock date and branch choice. This does not reserve a meeting.",
      href: "/appointments",
      icon: Calendar,
    },
    {
      title: "Support Request Form",
      category: "Mock form",
      description: "Create a sample ticket using synthetic details. No support reply is sent.",
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
        <h2 className="text-2xl md:text-3xl font-extrabold text-slate-900">Demo Workflows</h2>
        <p className="text-slate-500 text-sm mt-1">Explore mock land-record tasks. This is not an official registry service.</p>
      </div>

      <NoticeBanner 
        message="Use synthetic inputs only. These mock workflows do not issue official records, reserve appointments, or send support replies."
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
