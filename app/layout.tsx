import "./globals.css";
import React from "react";
import Link from "next/link";
import { Landmark } from "lucide-react";
import PrimaryNavigation from "@/components/PrimaryNavigation";

export const metadata = {
  title: "Land Records Demo Portal",
  description: "Land Records Demo Portal for sample registry searches, status tracking, and public service forms",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col bg-[#fcfcfc] text-[#1b1f24] antialiased hover:cursor-default">
        <a className="skip-link" href="#main-content">
          Skip to main content
        </a>
        <header className="border-b border-slate-800 bg-[#0f172a] text-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <Link href="/" className="flex min-w-0 items-center gap-2.5 group">
              <div className="p-2 rounded-lg bg-blue-600 text-white group-hover:bg-blue-500 transition-colors">
                <Landmark className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <span className="font-mono font-bold tracking-tight text-sm text-white block leading-none">
                  LRDP-PORTAL
                </span>
                <span className="text-[9px] text-slate-300 font-sans tracking-wider uppercase font-semibold">
                  Land Records Demo
                </span>
              </div>
            </Link>

            <PrimaryNavigation />
          </div>
        </header>

        <main className="flex-1" id="main-content" tabIndex={-1}>
          {children}
        </main>

        <footer className="border-t border-gray-200 bg-slate-50 py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-gray-500">
            <div className="flex min-w-0 items-start gap-2">
              <Landmark className="h-4 w-4 text-gray-400 shrink-0" />
              <span>&copy; {new Date().getFullYear()} Land Records Demo Portal. This is a demo portal. All records, submissions, and reference numbers are mock data for local testing only.</span>
            </div>
            
            <div className="flex flex-wrap justify-center gap-x-6 gap-y-2">
              <Link href="/demo-guide" className="hover:underline text-blue-600 font-bold focus:outline-none focus:ring-2 focus:ring-blue-500 px-1 py-0.5 rounded">Technical Notes</Link>
              <Link href="/support" className="hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 px-1 py-0.5 rounded">Support Desk</Link>
              <Link href="/transactions/status" className="hover:underline focus:outline-none focus:ring-2 focus:ring-blue-500 px-1 py-0.5 rounded">Track Status</Link>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
