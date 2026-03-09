import { NAV_ITEMS, SYSTEM_NAV_ITEMS } from '@/lib/constants'
import { SidebarNavItem } from './SidebarNavItem'
import { MLHealthWidget } from './MLHealthWidget'

export function Sidebar() {
  return (
    <aside className="w-[260px] bg-sidebar-bg flex-shrink-0 flex flex-col h-full border-r border-[#162e4d]">
      {/* Header */}
      <div className="h-20 flex flex-col justify-center px-6 border-b border-[#2d4a77] bg-[#162e4d]">
        <div className="flex items-center gap-2 mb-1">
          <span className="material-symbols-outlined text-primary text-[24px]">shield</span>
          <h1 className="text-white text-base font-bold leading-tight tracking-wide">
            WAF-ML SOC{' '}
            <span className="text-xs font-normal opacity-70 ml-1">v4.7</span>
          </h1>
        </div>
        <p className="text-blue-300 text-[11px] font-medium tracking-wide pl-8">
          Enterprise Security Console
        </p>
      </div>

      {/* Main nav */}
      <nav className="flex-1 py-4 flex flex-col gap-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => (
          <SidebarNavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
            badge={'badge' in item ? item.badge : undefined}
          />
        ))}

        {/* System section */}
        <div className="px-6 py-3 mt-2">
          <div className="h-px bg-[#2d4a77] mb-3" />
          <span className="text-[10px] uppercase tracking-wider text-blue-400 font-bold">
            System
          </span>
        </div>

        {SYSTEM_NAV_ITEMS.map((item) => (
          <SidebarNavItem
            key={item.href}
            href={item.href}
            icon={item.icon}
            label={item.label}
          />
        ))}
      </nav>

      {/* Bottom panel */}
      <div className="bg-[#162e4d] border-t border-[#2d4a77]">
        <MLHealthWidget />

        {/* User profile row */}
        <div className="px-4 py-3 bg-[#11243d] border-t border-[#2d4a77] flex items-center gap-3">
          <div className="h-8 w-8 rounded bg-blue-800 border border-blue-700 flex-shrink-0 flex items-center justify-center">
            <span className="text-xs font-bold text-blue-200">AC</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-medium text-white truncate">A. Chen</div>
            <div className="text-[10px] text-blue-300 truncate">SOC Analyst</div>
          </div>
          <button className="text-blue-400 hover:text-white transition-colors">
            <span className="material-symbols-outlined text-[16px]">settings</span>
          </button>
        </div>
      </div>
    </aside>
  )
}
