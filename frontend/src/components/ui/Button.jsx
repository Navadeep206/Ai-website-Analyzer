import React from 'react'

const VARIANT_CLASSES = {
  primary:
    'bg-indigo-600 text-white shadow-[0_1px_2px_rgba(15,23,42,0.12)] hover:bg-indigo-700 active:bg-indigo-800 border border-indigo-600',
  secondary:
    'bg-white text-slate-800 border border-slate-200 shadow-[0_1px_2px_rgba(15,23,42,0.04)] hover:bg-slate-50 hover:border-slate-300',
  subtle:
    'bg-indigo-50 text-indigo-700 border border-indigo-100 hover:bg-indigo-100/80',
  ghost:
    'bg-transparent text-slate-600 border border-transparent hover:bg-slate-100 hover:text-slate-900',
}

const SIZE_CLASSES = {
  sm: 'h-8 px-3 text-xs gap-1.5 rounded-md',
  md: 'h-10 px-4 text-sm gap-2 rounded-lg',
  lg: 'h-11 px-5 text-sm gap-2 rounded-lg',
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  type = 'button',
  className = '',
  disabled = false,
  ...props
}) {
  return (
    <button
      type={type}
      disabled={disabled}
      className={[
        'inline-flex items-center justify-center font-medium transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 focus-visible:ring-offset-1',
        'disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap',
        VARIANT_CLASSES[variant] || VARIANT_CLASSES.primary,
        SIZE_CLASSES[size] || SIZE_CLASSES.md,
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </button>
  )
}

