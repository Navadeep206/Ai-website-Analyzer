import React from 'react'
import { AnalysisHeader } from '../components/results/AnalysisHeader'
import { AudienceSection } from '../components/results/AudienceSection'
import { BrandOverview } from '../components/results/BrandOverview'
import { CompetitorSection } from '../components/results/CompetitorSection'
import { SearchQueriesSection } from '../components/results/SearchQueriesSection'
import { SEOSection } from '../components/results/SEOSection'
import { ServicesSection } from '../components/results/ServicesSection'

export function ResultsPage({ data, onStartNewAnalysis, onCopy }) {
  if (!data || typeof data !== 'object') {
    return null
  }

  const website = typeof data.website === 'string' ? data.website : ''
  const brand = data.brand && typeof data.brand === 'object' ? data.brand : {}
  const analysis =
    data.analysis && typeof data.analysis === 'object' ? data.analysis : {}

  const competitorAnalysis = analysis.competitor_analysis || null
  const searchQueries = Array.isArray(analysis.target_search_queries)
    ? analysis.target_search_queries
    : []
  const seo = analysis.seo_improvements || null
  const topServices = Array.isArray(analysis.top_services)
    ? analysis.top_services
    : []
  const targetAudience = analysis.target_audience || null

  const competitorCount = Array.isArray(competitorAnalysis?.competitors)
    ? competitorAnalysis.competitors.length
    : 0

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
      <AnalysisHeader
        data={data}
        website={website}
        brand={brand}
        onStartNewAnalysis={onStartNewAnalysis}
        onCopyUrl={onCopy}
      />

      <BrandOverview
        brand={brand}
        competitorAnalysis={competitorAnalysis}
        competitorCount={competitorCount}
        searchQueryCount={searchQueries.length}
        serviceCount={topServices.length}
      />

      <CompetitorSection competitorAnalysis={competitorAnalysis} />

      <SearchQueriesSection queries={searchQueries} onCopy={onCopy} />

      <SEOSection seo={seo} website={website} />

      <ServicesSection services={topServices} />

      <AudienceSection audience={targetAudience} />
    </div>
  )
}

