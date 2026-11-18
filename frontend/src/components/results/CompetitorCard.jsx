import React from 'react'
import { ShieldAlert, Sparkles } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { ExpandableText } from './ExpandableText'
import { asNonEmptyList, getSourceMeta } from '../../utils/resultsHelpers'

export function CompetitorCard({ competitor }) {
  if (!competitor) return null

  const verification = getSourceMeta(competitor.verification_status)
  const strengths = asNonEmptyList(competitor.key_strengths)
  const weaknesses = asNonEmptyList(competitor.potential_weaknesses)

  return (
    <article className="flex flex-col rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] transition-all duration-150 hover:border-slate-300/90 hover:shadow-[0_4px_12px_rgba(15,23,42,0.05)]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-slate-900 break-words">
            {competitor.name || 'Unnamed Competitor'}
          </h4>
          {competitor.category && (
            <p className="mt-0.5 text-xs text-slate-500">{competitor.category}</p>
          )}
        </div>

        {verification.label && (
          <Badge tone={verification.tone}>
            {!verification.isVerifiedOnSite && (
              <Sparkles className="h-3 w-3" aria-hidden="true" />
            )}
            {verification.label}
          </Badge>
        )}
      </div>

      {competitor.overview && (
        <div className="mt-3">
          <ExpandableText text={competitor.overview} maxLength={200} />
        </div>
      )}

      {competitor.reason_for_similarity && (
        <div className="mt-3 rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2.5">
          <p className="text-[11px] font-semibold text-slate-700">
            Why Relevant
          </p>
          <div className="mt-1">
            <ExpandableText
              text={competitor.reason_for_similarity}
              maxLength={180}
              className="text-xs leading-relaxed text-slate-600"
            />
          </div>
        </div>
      )}

      {competitor.competitive_comparison && (
        <div className="mt-3">
          <p className="text-[11px] font-semibold text-slate-700">
            Brand Comparison
          </p>
          <div className="mt-1">
            <ExpandableText
              text={competitor.competitive_comparison}
              maxLength={180}
              className="text-xs leading-relaxed text-slate-600"
            />
          </div>
        </div>
      )}

      {(strengths.length > 0 || weaknesses.length > 0) && (
        <div className="mt-4 grid gap-3 border-t border-slate-100 pt-3.5 sm:grid-cols-2">
          <div>
            <p className="mb-1.5 text-[11px] font-semibold text-slate-700">
              Key Strengths
            </p>
            {strengths.length > 0 ? (
              <ul className="space-y-1 text-xs text-slate-600">
                {strengths.map((item, idx) => (
                  <li key={`${item}-${idx}`} className="flex items-start gap-1.5">
                    <span
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500"
                      aria-hidden="true"
                    />
                    <span className="break-words">{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">None listed.</p>
            )}
          </div>

          <div>
            <p className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold text-slate-700">
              <ShieldAlert
                className="h-3 w-3 text-amber-500"
                aria-hidden="true"
              />
              Potential Weaknesses
            </p>
            {weaknesses.length > 0 ? (
              <ul className="space-y-1 text-xs text-slate-600">
                {weaknesses.map((item, idx) => (
                  <li key={`${item}-${idx}`} className="flex items-start gap-1.5">
                    <span
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400"
                      aria-hidden="true"
                    />
                    <span className="break-words">{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">None suggested.</p>
            )}
          </div>
        </div>
      )}
    </article>
  )
}

