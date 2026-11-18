import React, { useEffect, useState } from 'react'
import { ChevronRight, Menu, Plus } from 'lucide-react'
import { getHealthStatus } from '../../services/api'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'

const VIEW_TITLES = {
  dashboard: 'Analyze Website',
  results: 'Analysis Results',
}

const API_STATUS_META = {
  checking: { label: 'Checking API...', dotClass: 'bg-slate-400' },
  online: { label: 'API Online', dotClass: 'bg-emerald-500' },
  offline: { label: 'API Offline', dotClass: 'bg-rose-500' },
}

export function Header({ activeView, onOpenMobileMenu, onStartNewAnalysis }) {
  const [apiStatus, setApiStatus] = useState('checking')
  const pageTitle = VIEW_TITLES[activeView] || 'Analyze Website'

  useEffect(() => {
    const controller = new AbortController()
    let active = true

    getHealthStatus({ signal: controller.signal })
      .then(() => {
        if (active) setApiStatus('online')
      })
      .catch(() => {
        if (active) setApiStatus('offline')
      })

    return () => {
      active = false
      controller.abort()
    }
  }, [])

  const statusMeta = API_STATUS_META[apiStatus]

  return (
    <header className="sticky top-0 z-30 flex h-16 shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/85 px-4 backdrop-blur-sm sm:px-6 lg:px-8">
      <div className="flex items-center gap-3 min-w-0">
        <button
          type="button"
          onClick={onOpenMobileMenu}
          className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 lg:hidden"
          aria-label="Open navigation menu"
        >
          <Menu className="h-4 w-4" />
        </button>

        <nav aria-label="Breadcrumb" className="flex items-center gap-1.5 text-sm min-w-0">
          <span className="hidden text-slate-400 sm:inline">SiteLens AI</span>
          <ChevronRight
            className="hidden h-3.5 w-3.5 shrink-0 text-slate-300 sm:inline"
            aria-hidden="true"
          />
          <h1 className="truncate font-semibold tracking-tight text-slate-900">
            {pageTitle}
          </h1>
        </nav>
      </div>

      <div className="flex items-center gap-2.5">
        <Badge tone="subtle" className="hidden sm:inline-flex">
          <span
            className={`h-1.5 w-1.5 rounded-full ${statusMeta.dotClass}`}
            aria-hidden="true"
          />
          {statusMeta.label}
        </Badge>

        {activeView !== 'dashboard' && (
          <Button
            variant="primary"
            size="sm"
            onClick={onStartNewAnalysis}
          >
            <Plus className="h-3.5 w-3.5" aria-hidden="true" />
            New Analysis
          </Button>
        )}
      </div>
    </header>
  )
}
