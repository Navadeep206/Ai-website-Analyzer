import React, { useEffect } from 'react'
import {
  Globe,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from 'lucide-react'
import logoUrl from '../../assets/logo.svg'

export const NAV_ITEMS = [
  {
    id: 'dashboard',
    label: 'Analyze Website',
    description: 'Run a structured website analysis',
    icon: Globe,
  },
]

function SidebarContent({
  activeView,
  onSelectView,
  collapsed,
  onToggleCollapse,
  onCloseMobile,
  isMobile = false,
}) {
  const showLabels = isMobile || !collapsed

  return (
    <div className="flex h-full flex-col bg-white">
      {/* Brand header */}
      <div
        className={[
          'flex h-16 shrink-0 items-center border-b border-slate-200/80 px-4',
          showLabels ? 'justify-between' : 'justify-center',
        ].join(' ')}
      >
        <button
          type="button"
          onClick={() => {
            onSelectView('dashboard')
            if (isMobile) onCloseMobile?.()
          }}
          className="flex items-center gap-2.5 rounded-lg text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
          title="SiteLens AI"
        >
          <img
            src={logoUrl}
            alt="SiteLens AI logo"
            className="h-8 w-8 shrink-0 rounded-lg shadow-[0_1px_2px_rgba(79,70,229,0.25)]"
          />
          {showLabels && (
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="truncate text-sm font-semibold tracking-tight text-slate-900">
                  SiteLens AI
                </span>
              </div>
              <p className="truncate text-[11px] text-slate-500">
                Website Intelligence
              </p>
            </div>
          )}
        </button>

        {isMobile ? (
          <button
            type="button"
            onClick={onCloseMobile}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
            aria-label="Close navigation menu"
          >
            <X className="h-4 w-4" />
          </button>
        ) : showLabels ? (
          <button
            type="button"
            onClick={onToggleCollapse}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
            aria-label="Collapse sidebar"
            title="Collapse sidebar"
          >
            <PanelLeftClose className="h-4 w-4" />
          </button>
        ) : null}
      </div>

      {/* Primary navigation */}
      <nav
        aria-label="Primary navigation"
        className="flex-1 space-y-1 overflow-y-auto px-3 py-4"
      >
        {showLabels && (
          <p className="px-2.5 pb-1.5 text-[11px] font-medium uppercase tracking-wider text-slate-400">
            Workspace
          </p>
        )}

        {NAV_ITEMS.map((item) => {
          const Icon = item.icon
          const isActive = activeView === item.id

          return (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                onSelectView(item.id)
                if (isMobile) onCloseMobile?.()
              }}
              aria-current={isActive ? 'page' : undefined}
              title={!showLabels ? item.label : undefined}
              className={[
                'group flex w-full items-center rounded-lg px-2.5 py-2 text-sm font-medium transition-colors duration-150',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40',
                showLabels ? 'justify-between' : 'justify-center',
                isActive
                  ? 'bg-indigo-50/90 text-indigo-700'
                  : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900',
              ].join(' ')}
            >
              <span className="flex items-center gap-2.5 min-w-0">
                <Icon
                  className={[
                    'h-4 w-4 shrink-0 transition-colors',
                    isActive
                      ? 'text-indigo-600'
                      : 'text-slate-400 group-hover:text-slate-600',
                  ].join(' ')}
                  aria-hidden="true"
                />
                {showLabels && <span className="truncate">{item.label}</span>}
              </span>

              {showLabels && item.tag && (
                <span
                  className={[
                    'ml-2 rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                    isActive
                      ? 'bg-indigo-100 text-indigo-700'
                      : 'bg-slate-100 text-slate-500',
                  ].join(' ')}
                >
                  {item.tag}
                </span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Footer / expand trigger */}
      <div className="border-t border-slate-200/80 p-3">
        {!isMobile && !showLabels ? (
          <button
            type="button"
            onClick={onToggleCollapse}
            className="flex h-9 w-full items-center justify-center rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
            aria-label="Expand sidebar"
            title="Expand sidebar"
          >
            <PanelLeftOpen className="h-4 w-4" />
          </button>
        ) : (
          <div className="rounded-lg border border-slate-200/80 bg-slate-50/80 px-3 py-2.5">
            <div className="flex items-center justify-between text-xs font-medium text-slate-700">
              <span>SiteLens AI</span>
              <span className="text-[11px] font-normal text-slate-400">v1.0</span>
            </div>
            <p className="mt-0.5 text-[11px] leading-relaxed text-slate-500">
              Powered by FastAPI &amp; Gemini structured analysis
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

export function Sidebar({
  activeView,
  onSelectView,
  collapsed,
  onToggleCollapse,
  mobileOpen,
  onCloseMobile,
}) {
  useEffect(() => {
    if (!mobileOpen) return undefined
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onCloseMobile?.()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [mobileOpen, onCloseMobile])

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={[
          'hidden lg:flex lg:flex-col lg:shrink-0 border-r border-slate-200/80 bg-white transition-[width] duration-200 ease-out',
          collapsed ? 'w-[72px]' : 'w-64',
        ].join(' ')}
      >
        <SidebarContent
          activeView={activeView}
          onSelectView={onSelectView}
          collapsed={collapsed}
          onToggleCollapse={onToggleCollapse}
        />
      </aside>

      {/* Mobile slide-over drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 flex lg:hidden"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation menu"
        >
          <div
            className="fixed inset-0 bg-slate-900/25 backdrop-blur-[1px]"
            onClick={onCloseMobile}
            aria-hidden="true"
          />
          <aside className="relative z-50 flex w-68 max-w-[82vw] flex-col border-r border-slate-200 bg-white shadow-xl">
            <SidebarContent
              activeView={activeView}
              onSelectView={onSelectView}
              collapsed={false}
              onCloseMobile={onCloseMobile}
              isMobile
            />
          </aside>
        </div>
      )}
    </>
  )
}

