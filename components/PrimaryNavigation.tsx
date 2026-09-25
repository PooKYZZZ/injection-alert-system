'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { CalendarDays, Search, ShieldCheck, Ticket } from 'lucide-react';

const navItems = [
  { href: '/records/search', label: 'Search Records', Icon: Search },
  { href: '/transactions/status', label: 'Track Status', Icon: ShieldCheck },
  { href: '/appointments', label: 'Book Appointment', Icon: CalendarDays },
  { href: '/support', label: 'Support Desk', Icon: Ticket },
];

const linkBaseClass =
  'text-xs font-semibold transition-colors flex min-h-9 items-center gap-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded-md py-1.5 px-2.5';

export default function PrimaryNavigation() {
  const pathname = usePathname();
  const loginIsCurrent = pathname === '/login';

  return (
    <>
      <nav
        aria-label="Primary"
        className="flex flex-wrap items-center gap-2 lg:justify-center"
      >
        {navItems.map(({ href, label, Icon }) => {
          const isCurrent = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              aria-current={isCurrent ? 'page' : undefined}
              className={`${linkBaseClass} ${
                isCurrent
                  ? 'bg-slate-800 text-white'
                  : 'text-slate-200 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <Icon
                aria-hidden="true"
                className={`h-3.5 w-3.5 ${isCurrent ? 'text-white' : 'text-slate-400'}`}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">
        <Link
          href="/login"
          aria-current={loginIsCurrent ? 'page' : undefined}
          className={`min-h-9 inline-flex items-center px-3.5 py-1.5 rounded-md border text-xs font-semibold transition-all shadow-xs focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            loginIsCurrent
              ? 'border-slate-600 bg-slate-800 text-white'
              : 'border-slate-700 text-slate-200 hover:bg-slate-800 hover:text-white'
          }`}
        >
          Demo Login
        </Link>
      </div>
    </>
  );
}
