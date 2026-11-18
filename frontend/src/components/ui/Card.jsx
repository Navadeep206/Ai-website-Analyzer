import React from 'react'

export function Card({ children, className = '', hover = false, ...props }) {
  return (
    <div
      className={[
        'rounded-xl border border-slate-200/80 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)]',
        hover
          ? 'transition-all duration-150 hover:border-slate-300/90 hover:shadow-[0_4px_12px_rgba(15,23,42,0.06)]'
          : '',
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </div>
  )
}

export function CardHeader({ children, className = '' }) {
  return <div className={`p-5 pb-3 ${className}`}>{children}</div>
}

export function CardTitle({ children, className = '' }) {
  return (
    <h3 className={`text-sm font-semibold tracking-tight text-slate-900 ${className}`}>
      {children}
    </h3>
  )
}

export function CardDescription({ children, className = '' }) {
  return (
    <p className={`mt-1 text-xs leading-relaxed text-slate-500 ${className}`}>
      {children}
    </p>
  )
}

export function CardContent({ children, className = '' }) {
  return <div className={`px-5 pb-5 ${className}`}>{children}</div>
}

