import React from 'react'
import { FileText } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { ExpandableText } from './ExpandableText'
import { getPriorityTone } from '../../utils/resultsHelpers'

export function SEORecommendationCard({ item }) {
  if (!item) return null

  return (
    <article className="flex flex-col rounded-xl border border-slate-200/80 bg-white p-4 transition-all duration-150 hover:border-slate-300/90 hover:shadow-[0_2px_8px_rgba(15,23,42,0.04)]">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <FileText className="h-3.5 w-3.5 text-indigo-500" aria-hidden="true" />
          {item.content_type && <Badge tone="neutral">{item.content_type}</Badge>}
        </div>
        {item.priority && (
          <Badge tone={getPriorityTone(item.priority)}>
            {`${item.priority} Priority`}
          </Badge>
        )}
      </div>

      {item.suggested_title && (
        <h4 className="mt-2.5 text-sm font-semibold text-slate-900 break-words">
          {item.suggested_title}
        </h4>
      )}

      {item.purpose && (
        <div className="mt-1.5">
          <ExpandableText text={item.purpose} maxLength={160} />
        </div>
      )}

      {(item.target_keyword || item.target_audience) && (
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-100 pt-2.5 text-[11px] text-slate-500">
          {item.target_keyword && (
            <span>
              <span className="font-medium text-slate-700">Keyword: </span>
              {item.target_keyword}
            </span>
          )}
          {item.target_audience && (
            <span>
              <span className="font-medium text-slate-700">Audience: </span>
              {item.target_audience}
            </span>
          )}
        </div>
      )}
    </article>
  )
}
