import React from "react";
import Link from "next/link";
import type { Comment } from "@prisma/client";
import { 
  Search, 
  CalendarDays, 
  Ticket, 
  MessageSquare, 
  ArrowRight, 
  ShieldCheck, 
  FileText,
  Clock,
  MapPin,
  ClipboardCheck
} from "lucide-react";
import { SITE_CONFIG } from "../lib/demo-config";
import CommentsForm from "./CommentsForm";
import { prisma } from "@/lib/prisma";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  // Read comments from Prisma, fallback to empty array
  const comments: Comment[] = await prisma.comment.findMany({
    orderBy: { createdAt: "desc" },
    take: 5,
  });

  // Define tasks for easy mapping
  const TASKS = [
    {
      title: "Search Land Deeds",
      description: "Query publicly accessible cadastral indexes and registered land certificates in our demo database.",
      cta: "Search record indexes",
      href: "/records/search",
      metadata: "Instant lookup • No registration required",
      icon: Search,
    },
    {
      title: "Request a Certified Copy",
      description: "Request a demo copy summary for property transactions, verification, or personal records.",
      cta: "Request copy",
      href: "/records/LND-2026-0001", // Lead to records system where they inspect and click request copy
      metadata: "Takes 2–3 minutes • Requires a record number",
      icon: FileText,
    },
    {
      title: "Check Transaction Status",
      description: "Track the real-time processing state of support tickets, appointments, or copy requests under review.",
      cta: "Track status code",
      href: "/transactions/status",
      metadata: "Real-time update • Requires reference code",
      icon: ShieldCheck,
    },
    {
      title: "Book an Appointment",
      description: "Schedule a consultation or boundary arbitration session with regional registrar officers.",
      cta: "Book public session",
      href: "/appointments",
      metadata: "Mon–Fri, 8:00 AM – 5:00 PM • Selected branches",
      icon: CalendarDays,
    },
    {
      title: "Submit a Support Desk Ticket",
      description: "Report coordinate overlaps, missing land details, or registry index discrepancies to our software engineers.",
      cta: "Open system ticket",
      href: "/support",
      metadata: "Takes 2-3 minutes • Demo submission",
      icon: Ticket,
    },
  ];

  return (
    <div className="flex flex-col gap-12 pb-16 font-sans">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-slate-900 text-white py-16 sm:py-24">
        {/* Abstract background subtle texture */}
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px]"></div>
        
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-[10px] font-bold text-slate-300 mb-6 font-mono tracking-wider uppercase">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Land Records Demo Portal
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight max-w-4xl text-white">
            {SITE_CONFIG.name}
          </h1>
          
          <p className="mt-4 text-xs sm:text-sm text-slate-300 max-w-2xl text-center leading-relaxed">
            Authorized resource for searching sample cadastral indexes, booking registrar consultations, and tracking demo transaction records.
          </p>

          {/* Quick Stats Grid */}
          <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-6 w-full max-w-4xl pt-8 border-t border-slate-800">
            <div>
              <p className="text-2xl font-bold font-mono text-white">427,910</p>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mt-1">Deeds Registered</p>
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-white">2.8M</p>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mt-1">Hectares Covered</p>
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-white">100%</p>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mt-1">Sample Records</p>
            </div>
            <div>
              <p className="text-2xl font-bold font-mono text-white">4 Branches</p>
              <p className="text-[10px] text-slate-400 uppercase tracking-widest font-semibold mt-1">Regional Offices</p>
            </div>
          </div>
        </div>
      </section>

      {/* Task-Based Portal Services */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full" id="service-tasks">
        <div className="mb-8">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Citizen Core Tasks</h2>
          <p className="text-xs text-gray-500 mt-1 leading-relaxed">
            Select one of the online workflows below to submit a mock request or query public database indexes.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {TASKS.map((task, idx) => {
            const Icon = task.icon;
            return (
              <div 
                key={idx} 
                className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col justify-between hover:shadow-md hover:border-slate-300 transition-all shadow-xs"
              >
                <div>
                  <div className="h-10 w-10 text-slate-900 bg-slate-50 flex items-center justify-center rounded-lg border border-gray-200 mb-4">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-bold text-slate-900">{task.title}</h3>
                  <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">
                    {task.description}
                  </p>
                </div>
                
                <div className="mt-6 pt-4 border-t border-gray-50">
                  <span className="block text-[10px] font-medium text-amber-700 bg-amber-50/50 border border-amber-100 rounded px-2.5 py-1 mb-3 self-start max-w-max">
                    {task.metadata}
                  </span>
                  <Link
                    href={task.href}
                    className="inline-flex items-center gap-1 text-xs font-bold text-blue-600 hover:text-blue-800 group"
                  >
                    {task.cta}
                    <ArrowRight className="h-3 w-3 transform group-hover:translate-x-0.5 transition-transform" />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Calm Service Stepper section (Service Journey) */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full py-6">
        <div className="bg-slate-50 border border-gray-200 rounded-xl p-8 shadow-xs">
          <div className="mb-8 max-w-xl">
            <h2 className="text-sm font-bold uppercase tracking-widest text-slate-800 mb-1 flex items-center gap-2">
              <ClipboardCheck className="h-4 w-4 text-slate-600 font-bold" />
              Service Journey Pattern
            </h2>
            <p className="text-xs text-gray-400">
              Guidance flow describing the sequential lifecycle of typical registry files.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
            {/* Step 1 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-slate-800 text-white font-mono text-xs font-black flex items-center justify-center">
                  1
                </div>
                <h3 className="text-sm font-bold text-slate-900">Submit Request</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                Complete and submit the appropriate portal digital form, supplying valid property references.
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-slate-800 text-white font-mono text-xs font-black flex items-center justify-center">
                  2
                </div>
                <h3 className="text-sm font-bold text-slate-900">Obtain Reference</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                A non-volatile reference token gets generated for verification, logging, and status queries.
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-blue-600 text-white font-mono text-xs font-black flex items-center justify-center">
                  3
                </div>
                <h3 className="text-sm font-bold text-slate-900">Processing Review</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                Data is saved as mock records that follow normal registrar processing steps.
              </p>
            </div>

            {/* Step 4 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-slate-800 text-white font-mono text-xs font-black flex items-center justify-center">
                  4
                </div>
                <h3 className="text-sm font-bold text-slate-900">Track Processing</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                Track real-time status updates via reference lookup, or visit public surveyor branches.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Citizens Comments and Feedback Section */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="bg-slate-50 rounded-2xl border border-gray-200 p-6 md:p-8">
          <div className="flex items-center gap-2 mb-4">
            <MessageSquare className="h-5 w-5 text-slate-700" aria-hidden="true" />
            <h2 className="text-lg font-bold text-slate-900">Citizen Comments & Feedback</h2>
          </div>
          
          <p className="text-xs text-slate-500 mb-6 leading-relaxed">
            Read comments or share suggestions in the demo registry feedback board.
          </p>

          <div className="space-y-4 mb-8">
            {comments.map((comment, index) => (
              <div key={index} className="bg-white rounded-xl p-4 border border-gray-100 shadow-xs relative">
                <div className="flex items-center justify-between mb-1 text-xs">
                  <span className="font-semibold text-slate-900">{comment.displayName}</span>
                  <span className="text-[10px] text-gray-400 font-mono">{new Date(comment.createdAt).toLocaleString()}</span>
                </div>
                <p className="text-xs text-gray-600 leading-relaxed mt-1">{comment.message}</p>
              </div>
            ))}
          </div>

          <CommentsForm />
        </div>
      </section>
    </div>
  );
}
