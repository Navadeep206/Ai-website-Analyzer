import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { createServer } from 'vite'

import {
  buildSafeExportFilename,
  serializeAnalysisAsJson,
  serializeAnalysisAsMarkdown,
} from '../src/utils/exportAnalysis.js'
import {
  copyTextToClipboard,
  formatAllQueriesForCopy,
  getSourceMeta,
  isSafeExternalUrl,
} from '../src/utils/resultsHelpers.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = path.resolve(__dirname, '..')

function buildCompleteResponse() {
  return {
    success: true,
    website: 'https://www.acme.example/',
    brand: {
      name: 'Acme Cloud Analytics',
      category: 'SaaS Product Analytics',
      summary: 'Cloud analytics platform helping SaaS teams track funnels and retention cohorts.',
      source_type: 'website_identified',
    },
    analysis: {
      competitor_analysis: {
        brand_overview: 'Provides SaaS funnel monitoring and cohort dashboards.',
        competitors: [
          {
            name: 'Mixpanel',
            category: 'Product Analytics',
            overview: 'Event-based product analytics platform for digital teams.',
            key_strengths: ['Mature funnel reporting'],
            potential_weaknesses: ['Costs can rise at high event volumes'],
            competitive_comparison: 'Targets similar SaaS product teams.',
            verification_status: 'ai_suggested',
            reason_for_similarity: 'Overlaps on funnel and retention cohort tracking.',
          },
          {
            name: 'Amplitude',
            category: 'Digital Analytics',
            overview: 'Behavioral product analytics and experimentation suite.',
            key_strengths: ['Experimentation workflows'],
            potential_weaknesses: ['Complex setup for small startups'],
            competitive_comparison: 'Competes for growth teams.',
            verification_status: 'website_mentioned',
            reason_for_similarity: 'Mentioned directly in comparison guide.',
          },
        ],
        brand_strengths: ['Focused SaaS analytics workflows'],
        competitive_advantages: ['Sub-second cohort queries'],
        market_positioning: 'Lightweight AI-assisted analytics platform.',
        opportunities: ['Publish SaaS retention case studies'],
        limitations: null,
      },
      target_search_queries: [
        {
          query: 'best SaaS product analytics platform for startups',
          platforms: ['Google', 'LinkedIn'],
          intent: 'Commercial',
          business_relevance: 'Captures high-intent SaaS buyers.',
          target_audience: 'SaaS founders',
          source_type: 'ai_inferred',
        },
        {
          query: 'how to track SaaS retention cohorts',
          platforms: ['Google', 'X'],
          intent: 'Informational',
          business_relevance: 'Matches cohort analytics features.',
          target_audience: 'Product managers',
          source_type: 'ai_inferred',
        },
        {
          query: 'real-time SaaS funnel dashboard software',
          platforms: ['Google'],
          intent: 'Transactional',
          business_relevance: 'Matches buyers ready to adopt.',
          target_audience: 'Growth leads',
          source_type: 'ai_inferred',
        },
        {
          query: 'B2B SaaS analytics vendor',
          platforms: ['LinkedIn'],
          intent: 'Business Discovery',
          business_relevance: 'Supports vendor discovery.',
          target_audience: 'VP of Product',
          source_type: 'ai_inferred',
        },
        {
          query: 'SaaS retention dashboard layout examples',
          platforms: ['Instagram', 'Facebook'],
          intent: 'Inspiration',
          business_relevance: 'Attracts teams researching dashboard layouts.',
          target_audience: 'Growth marketers',
          source_type: 'ai_inferred',
        },
      ],
      seo_improvements: {
        keyword_recommendations: {
          primary_keyword: 'SaaS product analytics',
          secondary_keywords: ['SaaS retention cohort analytics'],
          long_tail_keywords: ['real-time funnel analytics for SaaS teams'],
          related_keywords: ['product telemetry dashboards'],
        },
        recommended_seo_title: {
          recommended_title: 'Acme Cloud Analytics | SaaS Product Analytics',
          primary_keyword: 'SaaS product analytics',
          reason: 'Pairs brand with primary commercial keyword.',
        },
        recommended_meta_description: {
          recommended_meta_description:
            'Monitor SaaS funnels and retention cohorts in real time with Acme Cloud Analytics.',
          target_keyword: 'SaaS funnels',
          explanation: 'Concise value summary without keyword stuffing.',
        },
        supporting_content: [
          {
            content_type: 'Service page',
            suggested_title: 'SaaS Retention Cohort Analytics',
            target_keyword: 'SaaS retention cohort analytics',
            purpose: 'Capture commercial search intent.',
            target_audience: 'Product managers',
            priority: 'High',
          },
        ],
        seo_issues: {
          observed_issues: ['Homepage lacks detailed pricing sections.'],
          recommended_improvements: ['Add feature-specific landing pages.'],
          potential_technical_audit_items: ['Verify XML sitemap and canonical tags.'],
        },
      },
      top_services: [
        {
          service_name: 'SaaS Funnel Monitoring',
          description: 'Tracks user conversion stages across SaaS workflows.',
          target_industry: ['B2B SaaS'],
          target_customer: ['Product teams'],
          main_benefit: 'Pinpoints conversion drop-offs rapidly.',
          source_type: 'website_identified',
          evidence: 'Monitors funnels and retention cohorts.',
        },
        {
          service_name: 'Telemetry Instrumentation Setup',
          description: 'Guided analytics event taxonomy implementation.',
          target_industry: ['B2B SaaS'],
          target_customer: ['Engineering teams'],
          main_benefit: 'Accelerates clean telemetry collection.',
          source_type: 'ai_inferred',
          evidence: null,
        },
      ],
      target_audience: {
        primary_audience: ['Growing SaaS teams'],
        secondary_audience: ['RevOps analysts'],
        industries: ['B2B SaaS'],
        business_types: ['SaaS startups'],
        customer_profiles: [
          {
            audience_segment: 'SaaS Growth Leaders',
            business_type: 'B2B SaaS Startup',
            industry: 'Cloud Software',
            customer_needs: ['Funnel clarity'],
            challenges: ['Slow manual reporting'],
            relevant_services: ['SaaS Funnel Monitoring'],
            marketing_recommendation: 'Publish cohort guides on LinkedIn.',
            source_type: 'website_identified',
          },
        ],
        customer_needs: ['Actionable funnel visibility'],
        customer_pain_points: ['Fragmented retention tracking'],
        potential_interests: ['Product-led growth'],
        geographical_focus: [],
        recommended_marketing_segments: ['B2B SaaS Heads of Product'],
        explicitly_identified_audiences: ['Growing SaaS teams'],
        inferred_audiences: ['RevOps analysts'],
      },
    },
  }
}

async function withResultsPage(fn) {
  const server = await createServer({
    root: FRONTEND_ROOT,
    server: { middlewareMode: true, hmr: false, ws: false },
    appType: 'custom',
    logLevel: 'error',
  })
  try {
    const { ResultsPage } = await server.ssrLoadModule('/src/pages/ResultsPage.jsx')
    return await fn(ResultsPage)
  } finally {
    await server.close()
  }
}

describe('Phase 9A.3 — Results Dashboard Helpers', () => {
  it('validates safe external HTTP/HTTPS URLs and blocks unsafe schemes', () => {
    assert.equal(isSafeExternalUrl('https://example.com/path'), true)
    assert.equal(isSafeExternalUrl('http://example.org'), true)
    assert.equal(isSafeExternalUrl('javascript:alert(1)'), false)
    assert.equal(isSafeExternalUrl('data:text/html,hi'), false)
    assert.equal(isSafeExternalUrl('file:///etc/passwd'), false)
    assert.equal(isSafeExternalUrl('not-a-url'), false)
    assert.equal(isSafeExternalUrl(''), false)
  })

  it('copies individual query and all five queries cleanly via clipboard', async () => {
    const copiedTexts = []
    const mockClipboard = {
      async writeText(value) {
        copiedTexts.push(value)
      },
    }

    const sample = buildCompleteResponse()
    const singleOk = await copyTextToClipboard(
      sample.analysis.target_search_queries[0].query,
      mockClipboard
    )
    assert.equal(singleOk, true)
    assert.equal(copiedTexts[0], 'best SaaS product analytics platform for startups')

    const allFormatted = formatAllQueriesForCopy(
      sample.analysis.target_search_queries
    )
    const allOk = await copyTextToClipboard(allFormatted, mockClipboard)
    assert.equal(allOk, true)
    assert.equal(allFormatted.split('\n').length, 5)
    assert.equal(copiedTexts[1], allFormatted)
  })

  it('never labels AI-suggested or AI-inferred entries as verified', () => {
    const aiSuggested = getSourceMeta('ai_suggested')
    assert.equal(aiSuggested.label, 'AI Suggested')
    assert.equal(aiSuggested.isVerifiedOnSite, false)

    const aiInferred = getSourceMeta('ai_inferred')
    assert.equal(aiInferred.label, 'AI Inferred')
    assert.equal(aiInferred.isVerifiedOnSite, false)

    const websiteId = getSourceMeta('website_identified')
    assert.equal(websiteId.label, 'Website Identified')
    assert.equal(websiteId.isVerifiedOnSite, true)
  })
})

describe('Phase 9A.3 — ResultsPage Rendering & Data Integrity', () => {
  it('renders complete response with all 6 sections, safe external link, copy buttons, and responsive classes', async () => {
    await withResultsPage((ResultsPage) => {
      const sample = buildCompleteResponse()
      const html = renderToString(
        React.createElement(ResultsPage, {
          data: sample,
          onStartNewAnalysis: () => {},
        })
      )

      // Header, safe external link attributes, copy URL, New Analysis
      assert.ok(html.includes('Analysis Complete'))
      assert.ok(html.includes('Acme Cloud Analytics'))
      assert.ok(html.includes('Copy URL'))
      assert.ok(html.includes('New Analysis'))
      assert.ok(
        html.includes(
          'href="https://www.acme.example/" target="_blank" rel="noopener noreferrer"'
        )
      )

      // Competitors: distinguishes AI Suggested vs Mentioned on Website
      assert.ok(html.includes('Mixpanel'))
      assert.ok(html.includes('AI Suggested'))
      assert.ok(html.includes('Mentioned on Website'))

      // All 5 search queries + Copy All button + platform badges
      assert.ok(html.includes('Copy All Queries'))
      for (const q of sample.analysis.target_search_queries) {
        assert.ok(html.includes(q.query))
      }

      // SEO snippet, keywords, priority, observed vs audit issues
      assert.ok(html.includes('Suggested Search Snippet Preview'))
      assert.ok(html.includes('High Priority'))
      assert.ok(html.includes('Observed On-Page Issues'))
      assert.ok(html.includes('Potential Technical Audit Items'))

      // Services: Website Identified vs AI Inferred
      assert.ok(html.includes('SaaS Funnel Monitoring'))
      assert.ok(html.includes('Website Identified'))
      assert.ok(html.includes('AI Inferred'))

      // Target audience: Explicit vs Inferred + Not specified geography
      assert.ok(html.includes('Explicitly Identified on Website'))
      assert.ok(html.includes('AI-Inferred Audiences'))
      assert.ok(html.includes('Not specified on website'))

      // Responsive & overflow-safe utility classes
      assert.ok(html.includes('break-all'))
      assert.ok(html.includes('break-words'))
      assert.ok(html.includes('md:grid-cols-2'))

      // Never leaks raw undefined
      assert.equal(html.includes('undefined'), false)
    })
  })

  it('handles missing optional fields, empty lists, and missing sections gracefully', async () => {
    await withResultsPage((ResultsPage) => {
      const sparse = {
        success: true,
        website: 'javascript:alert(1)', // Unsafe URL must NOT become clickable link
        brand: {
          name: 'Minimal Brand',
          category: '',
          summary: '',
        },
        analysis: {
          competitor_analysis: {
            brand_overview: '',
            competitors: [],
            brand_strengths: [],
            competitive_advantages: [],
            market_positioning: '',
            opportunities: [],
            limitations: 'Insufficient website content to identify competitors.',
          },
          target_search_queries: [],
          seo_improvements: null,
          top_services: [],
          target_audience: null,
        },
      }

      const html = renderToString(
        React.createElement(ResultsPage, {
          data: sparse,
          onStartNewAnalysis: () => {},
        })
      )

      assert.ok(html.includes('Minimal Brand'))
      assert.ok(html.includes('No competitors were suggested for this website'))
      assert.ok(html.includes('Insufficient website content to identify competitors.'))
      assert.ok(html.includes('No services were identified from this website'))
      assert.ok(html.includes('No SEO recommendations were included'))
      assert.ok(html.includes('No target audience insights were returned'))
      // Unsafe javascript: URL must NOT appear as an <a href>
      assert.equal(html.includes('href="javascript:alert(1)"'), false)
      assert.equal(html.includes('undefined'), false)
    })
  })

  it('truncates long descriptions with accessible Show more toggle', async () => {
    await withResultsPage((ResultsPage) => {
      const sample = buildCompleteResponse()
      sample.brand.summary = 'Enterprise cloud analytics '.repeat(25)
      const html = renderToString(
        React.createElement(ResultsPage, {
          data: sample,
          onStartNewAnalysis: () => {},
        })
      )

      assert.ok(html.includes('Show more'))
      assert.ok(html.includes('aria-expanded="false"'))
    })
  })
})

describe('Phase 9A.4 — Export Utilities, Cancellation & Accessibility Polish', () => {
  it('generates safe sanitized filenames for JSON and Markdown exports', () => {
    assert.equal(
      buildSafeExportFilename('Acme Cloud / Analytics?!', 'https://acme.example', 'json'),
      'sitelens-acme-cloud-analytics.json'
    )
    assert.equal(
      buildSafeExportFilename('../../etc/passwd', 'https://acme.example', 'md'),
      'sitelens-etc-passwd.md'
    )
    assert.equal(
      buildSafeExportFilename('', 'https://www.stripe.com/', 'json'),
      'sitelens-www-stripe-com.json'
    )
    assert.equal(
      buildSafeExportFilename('', '', 'md'),
      'sitelens-analysis.md'
    )
  })

  it('serializes complete response as valid JSON and accurate Markdown without fabricated metrics', () => {
    const sample = buildCompleteResponse()

    const jsonText = serializeAnalysisAsJson(sample)
    assert.deepEqual(JSON.parse(jsonText), sample)

    const md = serializeAnalysisAsMarkdown(sample)
    assert.ok(md.includes('# Acme Cloud Analytics'))
    assert.ok(md.includes('https://www.acme.example/'))
    assert.ok(md.includes('#### Mixpanel (AI Suggested)'))
    assert.ok(md.includes('#### Amplitude (Mentioned on Website)'))
    assert.ok(md.includes('## 2. Target Search Queries (5)'))
    assert.ok(md.includes('best SaaS product analytics platform for startups'))
    assert.ok(md.includes('## 3. SEO Recommendations'))
    assert.ok(md.includes('## 4. Top Services (2)'))
    assert.ok(md.includes('## 5. Target Audience Identification'))
    assert.ok(md.includes('Not specified on website'))
    assert.equal(md.includes('undefined'), false)
  })

  it('renders Export JSON / Export MD buttons, skip-to-main-content link, and indeterminate loading UI', async () => {
    const server = await createServer({
      root: FRONTEND_ROOT,
      server: { middlewareMode: true, hmr: false, ws: false },
      appType: 'custom',
      logLevel: 'error',
    })
    try {
      const { ResultsPage } = await server.ssrLoadModule('/src/pages/ResultsPage.jsx')
      const { AnalysisLoadingState } = await server.ssrLoadModule(
        '/src/components/analysis/AnalysisLoadingState.jsx'
      )
      const { default: App } = await server.ssrLoadModule('/src/App.jsx')
      const { createAnalysisRunner } = await server.ssrLoadModule(
        '/src/context/AnalysisContext.jsx'
      )

      const resultsHtml = renderToString(
        React.createElement(ResultsPage, {
          data: buildCompleteResponse(),
          onStartNewAnalysis: () => {},
        })
      )
      assert.ok(resultsHtml.includes('Export JSON'))
      assert.ok(resultsHtml.includes('Export MD'))

      const loadingHtml = renderToString(
        React.createElement(AnalysisLoadingState, {
          url: 'https://acme.example',
          onCancel: () => {},
        })
      )
      assert.ok(loadingHtml.includes('sitelens-indeterminate-bar'))
      assert.ok(loadingHtml.includes('Cancel'))
      assert.ok(loadingHtml.includes('visual estimates'))

      const appHtml = renderToString(React.createElement(App))
      assert.ok(appHtml.includes('Skip to main content'))
      assert.ok(appHtml.includes('id="main-content"'))

      // Verify in-flight cancellation aborts cleanly and resets runner state
      let cancelledCallbackFired = false
      const runner = createAnalysisRunner(
        (_url, { signal }) =>
          new Promise((_resolve, reject) => {
            signal.addEventListener('abort', () => {
              const err = new Error('Aborted')
              err.name = 'AbortError'
              reject(err)
            })
          })
      )
      const pending = runner.execute('https://acme.example', {
        onCancel: () => {
          cancelledCallbackFired = true
        },
      })
      assert.equal(runner.isInFlight(), true)
      runner.cancel()
      const outcome = await pending
      assert.equal(outcome.cancelled, true)
      assert.equal(cancelledCallbackFired, true)
      assert.equal(runner.isInFlight(), false)
    } finally {
      await server.close()
    }
  })
})
