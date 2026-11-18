import React from 'react'
import { CheckCircle2, Quote, Sparkles } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { ExpandableText } from './ExpandableText'
import { asNonEmptyList, getSourceMeta } from '../../utils/resultsHelpers'

export function ServiceCard({ service, index }) {
  if (!service) return null

  const source = getSourceMeta(service.source_type)
  const industries = asNonEmptyList(service.target_industry)
  const customers = asNonEmptyList(service.target_customer)

  return (
    <article className="flex flex-col rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] transition-all duration-150 hover:border-slate-300/90 hover:shadow-[0_4px_12px_rgba(15,23,42,0.05)]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="flex items-start gap-2.5 min-w-0">
          <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-slate-200 bg-slate-50 text-xs font-semibold text-slate-600">
            {index + 1}
          </span>
          <h4 className="text-sm font-semibold text-slate-900 break-words">
            {service.service_name || 'Unnamed Service'}
          </h4>
        </div>

        {source.label && (
          <Badge tone={source.tone}>
            {source.isVerifiedOnSite ? (
              <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
            ) : (
              <Sparkles className="h-3 w-3" aria-hidden="true" />
            )}
            {source.label}
          </Badge>
        )}
      </div>

      {service.description && (
        <div className="mt-3">
          <ExpandableText text={service.description} maxLength={200} />
        </div>
      )}

      {service.main_benefit && (
        <div className="mt-3 rounded-lg border border-indigo-100/90 bg-indigo-50/40 px-3 py-2 text-xs text-slate-700">
          <span className="font-semibold text-indigo-900">Main Benefit: </span>
          {service.main_benefit}
        </div>
      )}

      {service.evidence && (
        <div className="mt-3 flex items-start gap-2 rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2 text-[11px] leading-relaxed text-slate-600">
          <Quote
            className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400"
            aria-hidden="true"
          />
          <span className="italic break-words">{service.evidence}</span>
        </div>
      )}

      {(industries.length > 0 || customers.length > 0) && (
        <div className="mt-3.5 flex flex-wrap gap-1.5 border-t border-slate-100 pt-3">
          {industries.map((ind, idx) => (
            <Badge key={`ind-${ind}-${idx}`} tone="subtle">
              {ind}
            </Badge>
          ))}
          {customers.map((cust, idx) => (
            <Badge key={`cust-${cust}-${idx}`} tone="neutral">
              {cust}
            </Badge>
          ))}
        </div>
      )}
    </article>
  )
}

