import React from 'react'

export function Input({
  id,
  label,
  leadingIcon: LeadingIcon,
  trailingAction,
  error,
  hint,
  className = '',
  inputClassName = '',
  ...props
}) {
  return (
    <div className={`w-full ${className}`}>
      {label && (
        <label
          htmlFor={id}
          className="mb-1.5 block text-xs font-medium text-slate-700"
        >
          {label}
        </label>
      )}

      <div
        className={[
          'group relative flex items-center rounded-lg border bg-white transition-all duration-150',
          error
            ? 'border-rose-300 focus-within:border-rose-500 focus-within:ring-2 focus-within:ring-rose-500/20'
            : 'border-slate-200 hover:border-slate-300 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-500/20',
        ].join(' ')}
      >
        {LeadingIcon && (
          <span className="pointer-events-none flex items-center pl-3.5 text-slate-400 group-focus-within:text-indigo-500 transition-colors">
            <LeadingIcon className="h-4 w-4" aria-hidden="true" />
          </span>
        )}

        <input
          id={id}
          className={[
            'h-11 w-full bg-transparent text-sm text-slate-900 placeholder:text-slate-400',
            'focus:outline-none',
            LeadingIcon ? 'pl-2.5' : 'pl-3.5',
            trailingAction ? 'pr-10' : 'pr-3.5',
            inputClassName,
          ].join(' ')}
          {...props}
        />

        {trailingAction && (
          <div className="absolute right-2 flex items-center">{trailingAction}</div>
        )}
      </div>

      {error ? (
        <p className="mt-1.5 text-xs text-rose-600" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="mt-1.5 text-xs text-slate-500">{hint}</p>
      ) : null}
    </div>
  )
}

