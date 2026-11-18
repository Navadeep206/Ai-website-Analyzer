import React from 'react'
import { Badge } from '../ui/Badge'

export function SectionHeader({
  id,
  icon: Icon,
  title,
  description,
  badgeText,
  badgeTone = 'neutral',
  action,
}) {
  return (
    <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
      <div className="flex items-start gap-3 min-w-0">
        {Icon && (
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-indigo-100 bg-indigo-50/80 text-indigo-600">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </div>
        )}
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3
              id={id}
              className="text-base font-semibold tracking-tight text-slate-900"
            >
              {title}
            </h3>
            {badgeText && <Badge tone={badgeTone}>{badgeText}</Badge>}
          </div>
          {description && (
            <p className="mt-1 text-xs leading-relaxed text-slate-500">
              {description}
            </p>
          )}
        </div>
      </div>

      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

