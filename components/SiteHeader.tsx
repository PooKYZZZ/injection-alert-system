'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { FileText, Search, ClipboardList, Calendar, LifeBuoy, MessageSquare, LogIn, Award } from 'lucide-react';
import Container from './Container';

export default function SiteHeader() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Services', href: '/services', icon: FileText },
    { name: 'Search Records', href: '/records/search', icon: Search },
    { name: 'Transaction Status', href: '/transactions/status', icon: ClipboardList },
    { name: 'Appointments', href: '/appointments', icon: Calendar },
    { name: 'Support', href: '/support', icon: LifeBuoy },
    { name: 'Comments', href: '/comments', icon: MessageSquare },
    { name: 'Login', href: '/login', icon: LogIn },
  ];

  return (
    <header className="bg-[#002147] text-white border-b border-[#001733]">
      {/* Official Government Disclaimer Bar */}
      <div className="bg-[#001126] text-slate-300 text-xs py-1.5 px-4 text-center border-b border-[#000a1a]">
        <Container className="flex items-center justify-center gap-2">
          <Award className="w-4 h-4 text-amber-400" />
          <span>OFFICIAL DEMO PORTAL: local registry simulation only. No real transactions exist.</span>
        </Container>
      </div>

      <Container className="py-4">
        <div className="flex flex-col xl:flex-row xl:items-center xl:justify-between gap-4">
          {/* Logo / Brand */}
          <Link href="/" className="flex items-center gap-3 group shrink-0">
            <div className="w-9 h-9 bg-white/10 rounded flex items-center justify-center text-white font-bold tracking-wider text-sm shadow-sm group-hover:bg-white/20 transition-all border border-white/20">
              LRP
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white m-0 leading-tight uppercase">
                Land Records Demo Portal
              </h1>
              <p className="text-[11px] text-blue-200/85 m-0 leading-tight uppercase font-semibold tracking-wider">
                National Public Land-Registration Network
              </p>
            </div>
          </Link>

          {/* Navigation links */}
          <nav className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs uppercase tracking-wider font-bold">
            <Link 
              href="/" 
              className={`pb-1.5 border-b-2 transition-all duration-200 ${
                pathname === '/' 
                  ? 'text-white border-white' 
                  : 'text-blue-100/90 hover:text-white border-transparent hover:border-white/40'
              }`}
            >
              Home
            </Link>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1 pb-1.5 border-b-2 transition-all duration-200 ${
                    isActive 
                      ? 'text-white border-white' 
                      : 'text-blue-100/90 hover:text-white border-transparent hover:border-white/40'
                  }`}
                >
                  <Icon className="w-3.5 h-3.5 opacity-80" />
                  <span>{item.name}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </Container>
    </header>
  );
}
