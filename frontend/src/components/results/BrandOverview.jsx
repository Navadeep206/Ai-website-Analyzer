import React from 'react'
import { Building2, Compass } from 'lucide-react'
import { Card, CardContent, CardHeader } from '../ui/Card'
import { ExpandableText } from './ExpandableText'
import { SectionHeader } from './SectionHeader'

export function BrandOverview({
  brand,
  competitorAnalysis,
  searchQueryCount = 0,
  competitorCount = 0,
  serviceCount = 0,
}) {
  const hasSummary = Boolean(brand?.summary?.trim())
  const hasPositioning = Boolean(competitorAnalysis?.market_positioning?.trim())
  const hasBrandOverview =
    Boolean(competitorAnalysis?.brand_overview?.trim()) &&
    competitorAnalysis.brand_overview.trim() !== brand?.summary?.trim()

  return (
    <section id="section-overview" aria-labelledby="heading-overview">
      <Card>
        <CardHeader className="p-5 sm:p-6 pb-4">
          <SectionHeader
            id="heading-overview"
            icon={Building2}
            title="Brand Overview"
            description="Business identity and positioning grounded in extracted website content."
          />
        </CardHeader>

        <CardContent className="space-y-5 px-5 pb-5 sm:px-6 sm:pb-6">
          {hasSummary ? (
            <ExpandableText
              text={brand.summary}
              maxLength={320}
              className="text-sm leading-relaxed text-slate-700"
            />
          ) : (
            <p className="text-sm text-slate-500">
              No brand summary was provided for this website.
            </p>
          )}

          {(hasBrandOverview || hasPositioning) && (
            <div className="grid gap-4 md:grid-cols-2">
              {hasBrandOverview && (
                <div className="rounded-lg border border-slate-200/80 bg-slate-50/70 p-4">
                  <p className="text-xs font-semibold text-slate-800">
                    Website Offering Summary
                  </p>
                  <div className="mt-1.5">
                    <ExpandableText
                      text={competitorAnalysis.brand_overview}
                      maxLength={240}
                    />
                  </div>
                </div>
              )}

              {hasPositioning && (
                <div className="rounded-lg border border-slate-200/80 bg-slate-50/70 p-4">
                  <div className="flex items-center gap-1.5">
                    <Compass
                      className="h-3.5 w-3.5 text-indigo-600"
                      aria-hidden="true"
                    />
                    <p className="text-xs font-semibold text-slate-800">
                      Market Positioning
                    </p>
                  </div>
                  <div className="mt-1.5">
                    <ExpandableText
                      text={competitorAnalysis.market_positioning}
                      maxLength={240}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Factual structural counts (no invented scores or metrics) */}
          <div className="grid grid-cols-1 gap-3 border-t border-slate-100 pt-4 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-200/70 bg-white px-4 py-3">
              <p className="text-[11px] font-medium text-slate-500">
                Competitors Profiled
              </p>
              <p className="mt-0.5 text-lg font-semibold text-slate-900">
                {competitorCount}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-white px-4 py-3">
              <p className="text-[11px] font-medium text-slate-500">
                Target Search Queries
              </p>
              <p className="mt-0.5 text-lg font-semibold text-slate-900">
                {searchQueryCount}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200/70 bg-white px-4 py-3">
              <p className="text-[11px] font-medium text-slate-500">
                Services Listed
              </p>
              <p className="mt-0.5 text-lg font-semibold text-slate-900">
                {serviceCount}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  )
}

