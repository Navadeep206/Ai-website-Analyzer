import React from 'react'

const TONE_CLASSES = {
  neutral: 'bg-slate-100 text-slate-600 border-slate-200/80',
  indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200/70',
  subtle: 'bg-white text-slate-600 border-slate-200/80',
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200/70',
  amber: 'bg-amber-50 text-amber-800 border-amber-200/80',
  rose: 'bg-rose-50 text-rose-700 border-rose-200/70',
  sky: 'bg-sky-50 text-sky-700 border-sky-200/70',
}

export function Badge({ children, tone = 'neutral', className = '' }) {
  return (
    <span
      className={[
        'inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium leading-4',
        TONE_CLASSES[tone] || TONE_CLASSES.neutral,
        className,
      ].join(' ')}
    >
      {children}
    </span>
  )
}
