import React from 'react'
import { Info, Target } from 'lucide-react'
import { Card, CardContent, CardHeader } from '../ui/Card'
import { CompetitorCard } from './CompetitorCard'
import { BulletPanel } from './InsightPrimitives'
import { SectionHeader } from './SectionHeader'
import { asNonEmptyList } from '../../utils/resultsHelpers'

export function CompetitorSection({ competitorAnalysis }) {
  const competitors = Array.isArray(competitorAnalysis?.competitors)
    ? competitorAnalysis.competitors
    : []
  const strengths = asNonEmptyList(competitorAnalysis?.brand_strengths)
  const advantages = asNonEmptyList(competitorAnalysis?.competitive_advantages)
  const opportunities = asNonEmptyList(competitorAnalysis?.opportunities)

  return (
    <section id="section-competitors" aria-labelledby="heading-competitors">
      <Card>
        <CardHeader className="p-5 sm:p-6 pb-4">
          <SectionHeader
            id="heading-competitors"
            icon={Target}
            title="Competitor vs. Brand Analysis"
            description="AI-suggested market comparisons based on website positioning. Suggestions are not independent market research."
            badgeText={`${competitors.length} ${
              competitors.length === 1 ? 'competitor' : 'competitors'
            }`}
            badgeTone="neutral"
          />
        </CardHeader>

        <CardContent className="space-y-5 px-5 pb-5 sm:px-6 sm:pb-6">
          {(strengths.length > 0 ||
            advantages.length > 0 ||
            opportunities.length > 0) && (
            <div className="grid gap-3 md:grid-cols-3">
              <BulletPanel
                title="Brand Strengths"
                items={strengths}
                dotClass="bg-emerald-500"
                emptyText="None identified."
              />
              <BulletPanel
                title="Competitive Advantages"
                items={advantages}
                dotClass="bg-indigo-500"
                emptyText="None identified."
              />
              <BulletPanel
                title="Strategic Opportunities"
                items={opportunities}
                dotClass="bg-sky-500"
                emptyText="None identified."
              />
            </div>
          )}

          {competitorAnalysis?.limitations && (
            <div className="flex items-start gap-2.5 rounded-lg border border-amber-200/80 bg-amber-50/70 px-4 py-3 text-xs leading-relaxed text-amber-900">
              <Info
                className="mt-0.5 h-4 w-4 shrink-0 text-amber-600"
                aria-hidden="true"
              />
              <div>
                <span className="font-semibold">Analysis Note: </span>
                {competitorAnalysis.limitations}
              </div>
            </div>
          )}

          {competitors.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {competitors.map((comp, idx) => (
                <CompetitorCard
                  key={`${comp?.name || 'competitor'}-${idx}`}
                  competitor={comp}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-6 py-8 text-center">
              <p className="text-sm font-medium text-slate-700">
                No competitors were suggested for this website
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Available website content may have been too limited to recommend
                relevant competitors reliably.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  )
}

