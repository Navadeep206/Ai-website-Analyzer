import React from 'react'
import { CheckCircle2, Megaphone, Sparkles } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { ExpandableText } from './ExpandableText'
import { asNonEmptyList, getSourceMeta } from '../../utils/resultsHelpers'

export function AudienceCard({ profile }) {
  if (!profile) return null

  const source = getSourceMeta(profile.source_type)
  const needs = asNonEmptyList(profile.customer_needs)
  const challenges = asNonEmptyList(profile.challenges)
  const services = asNonEmptyList(profile.relevant_services)

  return (
    <article className="flex flex-col rounded-xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.03)] transition-all duration-150 hover:border-slate-300/90 hover:shadow-[0_4px_12px_rgba(15,23,42,0.05)]">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-slate-900 break-words">
            {profile.audience_segment || 'Audience Segment'}
          </h4>
          {(profile.business_type || profile.industry) && (
            <p className="mt-0.5 text-xs text-slate-500">
              {[profile.business_type, profile.industry].filter(Boolean).join(' · ')}
            </p>
          )}
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

      {(needs.length > 0 || challenges.length > 0) && (
        <div className="mt-3.5 grid gap-3 sm:grid-cols-2">
          <div>
            <p className="mb-1.5 text-[11px] font-semibold text-slate-700">
              Customer Needs
            </p>
            {needs.length > 0 ? (
              <ul className="space-y-1 text-xs text-slate-600">
                {needs.map((n, idx) => (
                  <li key={`${n}-${idx}`} className="flex items-start gap-1.5">
                    <span
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500"
                      aria-hidden="true"
                    />
                    <span className="break-words">{n}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">None listed.</p>
            )}
          </div>

          <div>
            <p className="mb-1.5 text-[11px] font-semibold text-slate-700">
              Challenges
            </p>
            {challenges.length > 0 ? (
              <ul className="space-y-1 text-xs text-slate-600">
                {challenges.map((c, idx) => (
                  <li key={`${c}-${idx}`} className="flex items-start gap-1.5">
                    <span
                      className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400"
                      aria-hidden="true"
                    />
                    <span className="break-words">{c}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400">None listed.</p>
            )}
          </div>
        </div>
      )}

      {services.length > 0 && (
        <div className="mt-3.5">
          <p className="mb-1.5 text-[11px] font-semibold text-slate-700">
            Relevant Services
          </p>
          <div className="flex flex-wrap gap-1.5">
            {services.map((srv, idx) => (
              <Badge key={`${srv}-${idx}`} tone="subtle">
                {srv}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {profile.marketing_recommendation && (
        <div className="mt-3.5 rounded-lg border border-slate-100 bg-slate-50/80 px-3 py-2.5">
          <div className="flex items-center gap-1.5">
            <Megaphone
              className="h-3.5 w-3.5 text-indigo-500"
              aria-hidden="true"
            />
            <p className="text-[11px] font-semibold text-slate-700">
              Marketing Recommendation
            </p>
          </div>
          <div className="mt-1">
            <ExpandableText
              text={profile.marketing_recommendation}
              maxLength={180}
            />
          </div>
        </div>
      )}
    </article>
  )
}

