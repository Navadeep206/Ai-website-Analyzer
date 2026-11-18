import React from 'react'
import { Check, Copy } from 'lucide-react'
import { useTransientFlag } from '../../hooks/useTransientFlag'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import {
  asNonEmptyList,
  copyTextToClipboard,
  getPlatformBadgeStyle,
  getSourceMeta,
} from '../../utils/resultsHelpers'

export function SearchQueryCard({
  item,
  index,
  onCopy = copyTextToClipboard,
}) {
  const [copied, triggerCopied] = useTransientFlag(false, 1800)

  if (!item?.query) return null

  const platforms = asNonEmptyList(item.platforms)
  const sourceMeta = getSourceMeta(item.source_type)

  const handleCopy = async () => {
    const ok = await onCopy(item.query)
    if (ok) {
      triggerCopied(true)
    }
  }

  return (
    <article className="rounded-xl border border-slate-200/80 bg-white p-4 transition-all duration-150 hover:border-slate-300/90 hover:shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div className="flex items-start gap-3 min-w-0">
          <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-indigo-100 bg-indigo-50 text-xs font-semibold text-indigo-700">
            {index + 1}
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 break-words">
              {item.query}
            </p>
            <div className="mt-2 flex flex-wrap items-center gap-1.5">
              {item.intent && <Badge tone="indigo">{item.intent}</Badge>}
              {platforms.map((platform) => (
                <Badge
                  key={platform}
                  tone={getPlatformBadgeStyle(platform)}
                >
                  {platform}
                </Badge>
              ))}
              {sourceMeta.label && (
                <Badge tone="subtle">{sourceMeta.label}</Badge>
              )}
            </div>
          </div>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={handleCopy}
          aria-label={`Copy search query: ${item.query}`}
          className="self-start shrink-0"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-600" aria-hidden="true" />
              <span className="text-emerald-700">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" aria-hidden="true" />
              Copy
            </>
          )}
        </Button>
      </div>

      {(item.business_relevance || item.target_audience) && (
        <div className="mt-3 grid gap-2 border-t border-slate-100 pt-3 text-xs sm:grid-cols-2">
          {item.business_relevance && (
            <p className="leading-relaxed text-slate-600">
              <span className="font-medium text-slate-800">Relevance: </span>
              {item.business_relevance}
            </p>
          )}
          {item.target_audience && (
            <p className="leading-relaxed text-slate-600">
              <span className="font-medium text-slate-800">Audience: </span>
              {item.target_audience}
            </p>
          )}
        </div>
      )}
    </article>
  )
}

