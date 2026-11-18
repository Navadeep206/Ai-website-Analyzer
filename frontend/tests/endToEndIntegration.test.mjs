import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { createServer } from 'vite'

import { analyzeWebsite } from '../src/services/api.js'
import {
  buildSafeExportFilename,
  serializeAnalysisAsJson,
  serializeAnalysisAsMarkdown,
} from '../src/utils/exportAnalysis.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = path.resolve(__dirname, '..')

function buildBackendResponse(overrides = {}) {
  return {
    success: true,
    website: 'https://www.acme.example/',
    brand: {
      name: 'Acme Cloud Analytics',
      category: 'SaaS Product Analytics',
      summary: 'Cloud analytics platform for SaaS funnel and cohort tracking.',
      source_type: 'website_identified',
    },
    analysis: {
      competitor_analysis: {
        brand_overview: 'Provides SaaS funnel and cohort dashboards.',
        competitors: [
          {
            name: 'Mixpanel',
            category: 'Product Analytics',
            overview: 'Event-based product analytics platform.',
            key_strengths: ['Mature funnel reporting'],
            potential_weaknesses: ['Costs scale with high event volume'],
            competitive_comparison: 'Targets similar SaaS teams.',
            verification_status: 'ai_suggested',
            reason_for_similarity: 'Overlaps on funnel and cohort tracking.',
          },
        ],
        brand_strengths: ['Focused SaaS analytics workflows'],
        competitive_advantages: ['Sub-second cohort queries'],
        market_positioning: 'Lightweight AI-assisted SaaS analytics platform.',
        opportunities: ['Publish SaaS retention benchmarks'],
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
          business_relevance: 'Connects educational searchers to cohort tracking.',
          target_audience: 'Product managers',
          source_type: 'ai_inferred',
        },
        {
          query: 'real-time SaaS funnel dashboard software',
          platforms: ['Google'],
          intent: 'Transactional',
          business_relevance: 'Targets ready-to-buy SaaS teams.',
          target_audience: 'Growth leads',
          source_type: 'ai_inferred',
        },
        {
          query: 'B2B SaaS analytics vendor',
          platforms: ['LinkedIn'],
          intent: 'Business Discovery',
          business_relevance: 'Supports vendor discovery on B2B networks.',
          target_audience: 'VP of Product',
          source_type: 'ai_inferred',
        },
        {
          query: 'SaaS retention dashboard layout examples',
          platforms: ['Instagram', 'Facebook'],
          intent: 'Inspiration',
          business_relevance: 'Showcases visual analytics layouts.',
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
          reason: 'Aligns brand with primary commercial keyword.',
        },
        recommended_meta_description: {
          recommended_meta_description:
            'Monitor SaaS funnels and retention cohorts with Acme Cloud Analytics.',
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
          recommended_improvements: ['Create feature-specific landing pages.'],
          potential_technical_audit_items: ['Verify XML sitemap and canonical tags.'],
        },
      },
      top_services: [
        {
          service_name: 'SaaS Funnel Monitoring',
          description: 'Tracks user conversion stages across SaaS workflows.',
          target_industry: ['B2B SaaS'],
          target_customer: ['Product teams'],
          main_benefit: 'Identifies conversion drop-offs rapidly.',
          source_type: 'website_identified',
          evidence: 'Monitors funnels and retention cohorts.',
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
    ...overrides,
  }
}

async function withSsrModules(fn) {
  const server = await createServer({
    root: FRONTEND_ROOT,
    server: { middlewareMode: true, hmr: false, ws: false },
    appType: 'custom',
    logLevel: 'error',
  })
  try {
    const contextMod = await server.ssrLoadModule('/src/context/AnalysisContext.jsx')
    const resultsMod = await server.ssrLoadModule('/src/pages/ResultsPage.jsx')
    return await fn({
      createAnalysisRunner: contextMod.createAnalysisRunner,
      ResultsPage: resultsMod.ResultsPage,
    })
  } finally {
    await server.close()
  }
}

describe('Phase 9A.5 — Mocked End-to-End Integration & Cancellation Freeze Audit', () => {
  it('completes full submit -> loading -> response -> dashboard render -> export flow', async () => {
    await withSsrModules(async ({ createAnalysisRunner, ResultsPage }) => {
      const sample = buildBackendResponse()
      const mockFetch = async () => ({
        ok: true,
        status: 200,
        async json() {
          return sample
        },
      })

      const state = { loading: false, result: null, error: null, url: '' }
      const runner = createAnalysisRunner((url, opts) =>
        analyzeWebsite(url, { ...opts, fetchImpl: mockFetch })
      )

      const outcome = await runner.execute('https://acme.example', {
        onStart: (u) => {
          state.url = u
          state.loading = true
          state.error = null
        },
        onSuccess: (d) => {
          state.result = d
        },
        onError: (e) => {
          state.error = e
        },
        onFinish: () => {
          state.loading = false
        },
      })

      assert.equal(outcome.ok, true)
      assert.equal(state.loading, false)
      assert.equal(state.error, null)
      assert.equal(state.result.website, 'https://www.acme.example/')

      // Render dashboard with real state and confirm all 5 sections + exports
      const html = renderToString(
        React.createElement(ResultsPage, {
          data: state.result,
          onStartNewAnalysis: () => {},
        })
      )
      assert.ok(html.includes('Competitor vs. Brand Analysis'))
      assert.ok(html.includes('Target Search Queries'))
      assert.ok(html.includes('SEO Recommendations'))
      assert.ok(html.includes('Top Services'))
      assert.ok(html.includes('Target Audience Identification'))
      assert.ok(html.includes('Export JSON'))
      assert.ok(html.includes('Export MD'))

      // Verify exported JSON and Markdown match stored state
      assert.deepEqual(JSON.parse(serializeAnalysisAsJson(state.result)), sample)
      assert.ok(
        serializeAnalysisAsMarkdown(state.result).includes('# Acme Cloud Analytics')
      )
      assert.equal(
        buildSafeExportFilename(state.result.brand.name, state.result.website, 'md'),
        'sitelens-acme-cloud-analytics.md'
      )
    })
  })

  it('classifies all backend HTTP errors (422, 413, 502, 503, 504, 500) and network/timeout failures accurately', async () => {
    await withSsrModules(async ({ createAnalysisRunner }) => {
      const httpCases = [
        [422, 'VALIDATION_ERROR', false],
        [413, 'WEBSITE_RESPONSE_TOO_LARGE', false],
        [502, 'WEBSITE_FETCH_FAILED', true],
        [503, 'LLM_NOT_CONFIGURED', true],
        [504, 'LLM_TIMEOUT', true],
        [500, 'INTERNAL_SERVER_ERROR', true],
      ]

      for (const [status, code, retryable] of httpCases) {
        const mockFetch = async () => ({
          ok: false,
          status,
          async json() {
            return {
              success: false,
              error: { code, message: `Safe backend message for ${code}` },
            }
          },
        })

        let capturedError = null
        let capturedResult = null
        const runner = createAnalysisRunner((url, opts) =>
          analyzeWebsite(url, { ...opts, fetchImpl: mockFetch })
        )
        const outcome = await runner.execute('https://acme.example', {
          onSuccess: (d) => {
            capturedResult = d
          },
          onError: (e) => {
            capturedError = e
          },
        })

        assert.equal(outcome.ok, false)
        assert.equal(capturedResult, null)
        assert.equal(capturedError.status, status)
        assert.equal(capturedError.code, code)
        assert.equal(capturedError.retryable, retryable)
      }

      // Connection refused / backend unavailable
      const refusedRunner = createAnalysisRunner((url, opts) =>
        analyzeWebsite(url, {
          ...opts,
          fetchImpl: async () => {
            const err = new TypeError('fetch failed')
            err.cause = { code: 'ECONNREFUSED' }
            throw err
          },
        })
      )
      const refused = await refusedRunner.execute('https://acme.example')
      assert.equal(refused.ok, false)
      assert.equal(refused.error.code, 'NETWORK_ERROR')
      assert.equal(refused.error.retryable, true)

      // Client timeout
      const timeoutRunner = createAnalysisRunner((url, opts) =>
        analyzeWebsite(url, {
          ...opts,
          timeoutMs: 20,
          fetchImpl: (_u, { signal }) =>
            new Promise((_res, rej) => {
              signal.addEventListener('abort', () => {
                const abortErr = new Error('Aborted')
                abortErr.name = 'AbortError'
                rej(abortErr)
              })
            }),
        })
      )
      const timedOut = await timeoutRunner.execute('https://acme.example')
      assert.equal(timedOut.ok, false)
      assert.equal(timedOut.error.status, 504)
      assert.equal(timedOut.error.code, 'CLIENT_TIMEOUT')
      assert.equal(timedOut.error.retryable, true)
    })
  })

  it('prevents stale response after cancel from overwriting state AND allows starting a new analysis immediately', async () => {
    await withSsrModules(async ({ createAnalysisRunner }) => {
      let resolveFirst
      let callCount = 0

      const mockAnalyze = (url) => {
        callCount += 1
        if (callCount === 1) {
          // Simulates a request whose response resolves right after cancel()
          return new Promise((resolve) => {
            resolveFirst = () =>
              resolve(
                buildBackendResponse({
                  website: 'https://stale-first.example/',
                  brand: {
                    name: 'STALE FIRST BRAND',
                    category: 'Stale',
                    summary: 'Should never overwrite state',
                    source_type: 'website_identified',
                  },
                })
              )
          })
        }
        return Promise.resolve(
          buildBackendResponse({
            website: 'https://fresh-second.example/',
            brand: {
              name: 'FRESH SECOND BRAND',
              category: 'Fresh',
              summary: 'Fresh result after cancel',
              source_type: 'website_identified',
            },
          })
        )
      }

      const state = { loading: false, result: null, error: null }
      const callbacks = {
        onStart: () => {
          state.loading = true
          state.error = null
        },
        onSuccess: (d) => {
          state.result = d
        },
        onError: (e) => {
          state.error = e
        },
        onFinish: () => {
          state.loading = false
        },
      }

      const runner = createAnalysisRunner(mockAnalyze)

      // 1. Start first request
      const firstPromise = runner.execute('https://stale-first.example', callbacks)
      assert.equal(runner.isInFlight(), true)

      // 2. Cancel first request
      runner.cancel()
      state.loading = false
      assert.equal(runner.isInFlight(), false)

      // 3. Immediately start second request before first settles
      const secondOutcome = await runner.execute(
        'https://fresh-second.example',
        callbacks
      )
      assert.equal(secondOutcome.ok, true)
      assert.equal(state.result.brand.name, 'FRESH SECOND BRAND')
      assert.equal(state.loading, false)

      // 4. Now let the stale first request resolve — must NOT overwrite fresh state!
      resolveFirst()
      const firstOutcome = await firstPromise
      assert.equal(firstOutcome.cancelled, true)
      assert.equal(firstOutcome.ok, false)
      assert.equal(state.result.brand.name, 'FRESH SECOND BRAND')
      assert.equal(state.result.website, 'https://fresh-second.example/')
      assert.equal(state.error, null)
    })
  })

  it('blocks duplicate concurrent requests from rapid clicks', async () => {
    await withSsrModules(async ({ createAnalysisRunner }) => {
      let fetchCalls = 0
      let release
      const runner = createAnalysisRunner(() => {
        fetchCalls += 1
        return new Promise((resolve) => {
          release = () => resolve(buildBackendResponse())
        })
      })

      const p1 = runner.execute('https://acme.example')
      const dup1 = await runner.execute('https://acme.example')
      const dup2 = await runner.execute('https://acme.example')

      assert.equal(dup1.skipped, true)
      assert.equal(dup2.skipped, true)
      assert.equal(fetchCalls, 1)

      release()
      const res1 = await p1
      assert.equal(res1.ok, true)
    })
  })
})

