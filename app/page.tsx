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
      description: "Search the sample records included with this demo.",
      cta: "Search records",
      href: "/records/search",
      icon: Search,
    },
    {
      title: "Request a Sample Copy",
      description: "Create a mock copy request for the sample record.",
      cta: "Request sample copy",
      href: "/records/LND-2026-0001", // Lead to records system where they inspect and click request copy
      icon: FileText,
    },
    {
      title: "Track Demo Status",
      description: "Look up a mock support, appointment, or copy request by reference number.",
      cta: "Track demo status",
      href: "/transactions/status",
      icon: ShieldCheck,
    },
    {
      title: "Test an Appointment Request",
      description: "Submit a mock date and branch choice. No appointment is reserved.",
      cta: "Send demo request",
      href: "/appointments",
      icon: CalendarDays,
    },
    {
      title: "Submit a Support Request",
      description: "Create a mock ticket using synthetic details. No reply is sent.",
      cta: "Send demo request",
      href: "/support",
      icon: Ticket,
    },
  ];

  return (
    <div className="flex flex-col gap-8 pb-16 font-sans sm:gap-12">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-slate-900 text-white py-8 sm:py-16">
        {/* Abstract background subtle texture */}
        <div className="absolute inset-0 opacity-10 bg-[radial-gradient(#e5e7eb_1px,transparent_1px)] [background-size:16px_16px]"></div>
        
        <div className="relative max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 text-center flex flex-col items-center">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-800 border border-slate-700 text-[10px] font-bold text-slate-300 mb-4 font-mono tracking-wider uppercase">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Land Records Demo Portal
          </div>

          <h1 className="text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight max-w-4xl text-white">
            {SITE_CONFIG.name}
          </h1>
          
          <p className="mt-3 text-xs sm:text-sm text-slate-300 max-w-2xl text-center leading-relaxed">
            A CyberTrace test demo, not an official registry. Use synthetic inputs to explore mock land-record workflows.
          </p>
        </div>
      </section>

      {/* Task-Based Portal Services */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full" id="service-tasks">
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Choose a Demo Workflow</h2>
          <p className="text-xs text-gray-500 mt-1 leading-relaxed">
            Use synthetic inputs to explore the mock workflows.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {TASKS.map((task, idx) => {
            const Icon = task.icon;
            return (
              <div 
                key={idx} 
                className="bg-white rounded-xl border border-gray-200 p-5 sm:p-6 flex flex-col justify-between hover:shadow-md hover:border-slate-300 transition-all shadow-xs"
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
              What happens in this test portal.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 relative">
            {/* Step 1 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-slate-800 text-white font-mono text-xs font-black flex items-center justify-center">
                  1
                </div>
                <h3 className="text-sm font-bold text-slate-900">Choose a workflow</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                Open a mock search or service form.
              </p>
            </div>

            {/* Step 2 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-slate-800 text-white font-mono text-xs font-black flex items-center justify-center">
                  2
                </div>
                <h3 className="text-sm font-bold text-slate-900">Send synthetic input</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                Use test values only. Do not enter real personal or property details.
              </p>
            </div>

            {/* Step 3 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-blue-600 text-white font-mono text-xs font-black flex items-center justify-center">
                  3
                </div>
                <h3 className="text-sm font-bold text-slate-900">View the response</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                The portal shows a mock confirmation or form feedback.
              </p>
            </div>

            {/* Step 4 */}
            <div className="relative flex flex-col gap-2.5">
              <div className="flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-slate-800 text-white font-mono text-xs font-black flex items-center justify-center">
                  4
                </div>
                <h3 className="text-sm font-bold text-slate-900">Check demo status</h3>
              </div>
              <p className="text-xs text-gray-500 leading-relaxed pl-11 md:pl-0">
                Look up a sample status by reference. Updates are not live.
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
            <h2 className="text-lg font-bold text-slate-900">Demo Comments & Feedback</h2>
          </div>
          
          <p className="text-xs text-slate-500 mb-6 leading-relaxed">
            Read demo comments or share feedback about testing this portal.
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
