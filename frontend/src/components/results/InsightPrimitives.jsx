import React from 'react'
import { Badge } from '../ui/Badge'

export function TagBucket({
  label,
  items,
  tone = 'neutral',
  emptyText = 'None provided.',
}) {
  return (
    <div>
      <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      {items.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {items.map((item, idx) => (
            <Badge key={`${item}-${idx}`} tone={tone}>
              {item}
            </Badge>
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-400">{emptyText}</p>
      )}
    </div>
  )
}

export function BulletPanel({
  title,
  items,
  dotClass,
  emptyText = 'None reported.',
}) {
  return (
    <div className="rounded-lg border border-slate-200/70 bg-slate-50/60 p-4">
      <p className="mb-2 text-xs font-semibold text-slate-800">{title}</p>
      {items.length > 0 ? (
        <ul className="space-y-1.5 text-xs leading-relaxed text-slate-600">
          {items.map((item, idx) => (
            <li key={`${item}-${idx}`} className="flex items-start gap-2">
              <span
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dotClass}`}
                aria-hidden="true"
              />
              <span className="break-words">{item}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-slate-400">{emptyText}</p>
      )}
    </div>
  )
}

