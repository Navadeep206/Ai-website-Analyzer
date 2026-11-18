import React from 'react'
import { AlertTriangle, CheckSquare, SearchCheck, TrendingUp } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Card, CardContent, CardHeader } from '../ui/Card'
import { ExpandableText } from './ExpandableText'
import { TagBucket } from './InsightPrimitives'
import { SectionHeader } from './SectionHeader'
import { SEORecommendationCard } from './SEORecommendationCard'
import { asNonEmptyList } from '../../utils/resultsHelpers'

function AuditColumn({ title, subtitle, items, icon: Icon, iconClass }) {
  return (
    <div className="rounded-xl border border-slate-200/80 bg-slate-50/60 p-4">
      <div className="flex items-center gap-1.5">
        <Icon className={`h-3.5 w-3.5 ${iconClass}`} aria-hidden="true" />
        <p className="text-xs font-semibold text-slate-800">{title}</p>
      </div>
      <p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p>
      {items.length > 0 ? (
        <ul className="mt-3 space-y-1.5 text-xs leading-relaxed text-slate-600">
          {items.map((entry, idx) => (
            <li key={`${entry}-${idx}`} className="flex items-start gap-2">
              <span
                className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-slate-400"
                aria-hidden="true"
              />
              <span className="break-words">{entry}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-3 text-xs text-slate-400">None reported.</p>
      )}
    </div>
  )
}

export function SEOSection({ seo, website }) {
  if (!seo) {
    return (
      <section id="section-seo" aria-labelledby="heading-seo">
        <Card>
          <CardHeader className="p-5 sm:p-6">
            <SectionHeader
              id="heading-seo"
              icon={TrendingUp}
              title="SEO Recommendations"
              description="No SEO recommendations were included in this response."
            />
          </CardHeader>
        </Card>
      </section>
    )
  }

  const keywords = seo.keyword_recommendations
  const titleRec = seo.recommended_seo_title
  const metaRec = seo.recommended_meta_description
  const supportingContent = Array.isArray(seo.supporting_content)
    ? seo.supporting_content
    : []
  const observedIssues = asNonEmptyList(seo.seo_issues?.observed_issues)
  const recommendedImprovements = asNonEmptyList(
    seo.seo_issues?.recommended_improvements
  )
  const technicalAuditItems = asNonEmptyList(
    seo.seo_issues?.potential_technical_audit_items
  )

  return (
    <section id="section-seo" aria-labelledby="heading-seo">
      <Card>
        <CardHeader className="p-5 sm:p-6 pb-4">
          <SectionHeader
            id="heading-seo"
            icon={TrendingUp}
            title="SEO Recommendations"
            description="Actionable on-page metadata, keyword targeting, content roadmap, and audit observations."
            badgeText={
              supportingContent.length > 0
                ? `${supportingContent.length} content ideas`
                : undefined
            }
          />
        </CardHeader>

        <CardContent className="space-y-6 px-5 pb-5 sm:px-6 sm:pb-6">
          {/* SERP Snippet & Metadata Recommendations */}
          {(titleRec || metaRec) && (
            <div className="space-y-4">
              <div className="rounded-xl border border-slate-200/80 bg-slate-50/70 p-4 sm:p-5">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Suggested Search Snippet Preview
                </p>
                {website && (
                  <p className="mt-2 truncate text-xs text-emerald-700">
                    {website}
                  </p>
                )}
                {titleRec?.recommended_title && (
                  <p className="mt-0.5 text-base font-semibold text-indigo-700 break-words">
                    {titleRec.recommended_title}
                  </p>
                )}
                {metaRec?.recommended_meta_description && (
                  <p className="mt-1 text-xs leading-relaxed text-slate-600">
                    {metaRec.recommended_meta_description}
                  </p>
                )}
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {titleRec && (
                  <div className="rounded-lg border border-slate-200/80 bg-white p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-slate-800">
                        Title Rationale
                      </p>
                      {titleRec.primary_keyword && (
                        <Badge tone="indigo">{titleRec.primary_keyword}</Badge>
                      )}
                    </div>
                    <div className="mt-2">
                      <ExpandableText text={titleRec.reason} maxLength={180} />
                    </div>
                  </div>
                )}

                {metaRec && (
                  <div className="rounded-lg border border-slate-200/80 bg-white p-4">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-slate-800">
                        Meta Description Rationale
                      </p>
                      {metaRec.target_keyword && (
                        <Badge tone="indigo">{metaRec.target_keyword}</Badge>
                      )}
                    </div>
                    <div className="mt-2">
                      <ExpandableText text={metaRec.explanation} maxLength={180} />
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Keyword Strategy */}
          {keywords && (
            <div className="space-y-4 border-t border-slate-100 pt-5">
              <p className="text-xs font-semibold text-slate-900">
                Keyword Recommendations
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                <TagBucket
                  label="Primary Keyword"
                  items={
                    keywords.primary_keyword ? [keywords.primary_keyword] : []
                  }
                  tone="indigo"
                />
                <TagBucket
                  label="Secondary Keywords"
                  items={asNonEmptyList(keywords.secondary_keywords)}
                  tone="subtle"
                />
                <TagBucket
                  label="Long-Tail Keywords"
                  items={asNonEmptyList(keywords.long_tail_keywords)}
                  tone="neutral"
                />
                <TagBucket
                  label="Related Keywords"
                  items={asNonEmptyList(keywords.related_keywords)}
                  tone="neutral"
                />
              </div>
            </div>
          )}

          {/* Supporting Content Plan */}
          <div className="space-y-3 border-t border-slate-100 pt-5">
            <p className="text-xs font-semibold text-slate-900">
              Supporting Content Recommendations
            </p>
            {supportingContent.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {supportingContent.map((item, idx) => (
                  <SEORecommendationCard
                    key={`${item?.suggested_title || 'content'}-${idx}`}
                    item={item}
                  />
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                No supporting content recommendations were provided.
              </p>
            )}
          </div>

          {/* SEO Issues Breakdown */}
          <div className="space-y-3 border-t border-slate-100 pt-5">
            <p className="text-xs font-semibold text-slate-900">
              SEO Observations &amp; Audit Checklist
            </p>
            <div className="grid gap-4 md:grid-cols-3">
              <AuditColumn
                title="Observed On-Page Issues"
                subtitle="Directly visible in extracted HTML"
                items={observedIssues}
                icon={AlertTriangle}
                iconClass="text-amber-500"
              />
              <AuditColumn
                title="Recommended Improvements"
                subtitle="Practical next actions (not yet completed)"
                items={recommendedImprovements}
                icon={CheckSquare}
                iconClass="text-indigo-500"
              />
              <AuditColumn
                title="Potential Technical Audit Items"
                subtitle="Requires external crawl or tooling to verify"
                items={technicalAuditItems}
                icon={SearchCheck}
                iconClass="text-slate-500"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}

