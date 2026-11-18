import React, { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'

export function ExpandableText({
  text,
  maxLength = 220,
  className = 'text-xs leading-relaxed text-slate-600',
}) {
  const [expanded, setExpanded] = useState(false)

  if (typeof text !== 'string' || !text.trim()) {
    return null
  }

  const cleanText = text.trim()
  const needsTruncation = cleanText.length > maxLength

  if (!needsTruncation) {
    return <p className={className}>{cleanText}</p>
  }

  const displayedText = expanded
    ? cleanText
    : `${cleanText.slice(0, maxLength).trimEnd()}…`

  return (
    <div>
      <p className={className}>{displayedText}</p>
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        className="mt-1.5 inline-flex items-center gap-1 text-[11px] font-medium text-indigo-600 hover:text-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 rounded"
      >
        {expanded ? (
          <>
            Show less
            <ChevronUp className="h-3 w-3" aria-hidden="true" />
          </>
        ) : (
          <>
            Show more
            <ChevronDown className="h-3 w-3" aria-hidden="true" />
          </>
        )}
      </button>
    </div>
  )
}

