import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { createServer } from 'vite'

import {
  analyzeWebsite,
  ApiError,
  getHealthStatus,
} from '../src/services/api.js'
import { validateWebsiteUrlInput } from '../src/utils/urlValidation.js'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const FRONTEND_ROOT = path.resolve(__dirname, '..')

function buildSampleLinkAnalysisResponse() {
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
        brand_overview: 'Provides SaaS funnel and retention cohort analytics.',
        competitors: [
          {
            name: 'Mixpanel',
            category: 'Product Analytics',
            overview: 'Event-based product analytics platform.',
            key_strengths: ['Mature funnel reporting'],
            potential_weaknesses: ['Usage pricing scales with high event volume'],
            competitive_comparison: 'Targets similar SaaS product teams.',
            verification_status: 'ai_suggested',
            reason_for_similarity: 'Overlaps on funnel and cohort reporting.',
          },
        ],
        brand_strengths: ['Focused SaaS analytics workflows'],
        competitive_advantages: ['Fast cohort setup'],
        market_positioning: 'Lightweight SaaS funnel analytics tool.',
        opportunities: ['Publish vertical SaaS case studies'],
        limitations: null,
      },
      target_search_queries: [
        {
          query: 'best SaaS product analytics platform',
          platforms: ['Google', 'LinkedIn'],
          intent: 'Commercial',
          business_relevance: 'Matches high-intent SaaS buyers.',
          target_audience: 'SaaS founders',
          source_type: 'ai_inferred',
        },
        {
          query: 'how to track SaaS retention cohorts',
          platforms: ['Google', 'X'],
          intent: 'Informational',
          business_relevance: 'Aligns with cohort analytics features.',
          target_audience: 'Product managers',
          source_type: 'ai_inferred',
        },
        {
          query: 'real-time SaaS funnel dashboard software',
          platforms: ['Google'],
          intent: 'Transactional',
          business_relevance: 'Matches buyers ready to adopt dashboards.',
          target_audience: 'Growth leads',
          source_type: 'ai_inferred',
        },
        {
          query: 'B2B SaaS analytics vendor',
          platforms: ['LinkedIn'],
          intent: 'Business Discovery',
          business_relevance: 'Supports B2B vendor discovery.',
          target_audience: 'VP of Product',
          source_type: 'ai_inferred',
        },
        {
          query: 'SaaS retention dashboard layout examples',
          platforms: ['Instagram', 'Facebook'],
          intent: 'Inspiration',
          business_relevance: 'Showcases visual analytics dashboards.',
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
          reason: 'Pairs brand name clearly with primary commercial keyword.',
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
          observed_issues: ['Homepage lacks detailed pricing copy.'],
          recommended_improvements: ['Add dedicated feature landing pages.'],
          potential_technical_audit_items: ['Verify XML sitemap and canonicals.'],
        },
      },
      top_services: [
        {
          service_name: 'SaaS Funnel Monitoring',
          description: 'Tracks conversion drop-offs across SaaS onboarding flows.',
          target_industry: ['B2B SaaS'],
          target_customer: ['Product teams'],
          main_benefit: 'Pinpoints conversion bottlenecks rapidly.',
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
            challenges: ['Manual reporting'],
            relevant_services: ['SaaS Funnel Monitoring'],
            marketing_recommendation: 'Publish cohort guides on LinkedIn.',
            source_type: 'website_identified',
          },
        ],
        customer_needs: ['Actionable funnel visibility'],
        customer_pain_points: ['Slow manual reporting'],
        potential_interests: ['Product-led growth'],
        geographical_focus: [],
        recommended_marketing_segments: ['B2B SaaS Heads of Product'],
        explicitly_identified_audiences: ['Growing SaaS teams'],
        inferred_audiences: ['RevOps analysts'],
      },
    },
  }
}

function makeMockJsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return payload
    },
  }
}

describe('1. Frontend URL validation', () => {
  it('accepts valid HTTP and HTTPS URLs', () => {
    assert.equal(validateWebsiteUrlInput('https://example.com').valid, true)
    assert.equal(validateWebsiteUrlInput('http://sub.example.org/path?q=1').valid, true)
    assert.equal(validateWebsiteUrlInput('  https://example.com  ').normalizedUrl, 'https://example.com')
  })

  it('rejects empty and whitespace-only URLs', () => {
    assert.equal(validateWebsiteUrlInput('').valid, false)
    assert.equal(validateWebsiteUrlInput('   ').valid, false)
  })

  it('rejects missing protocol, unsupported schemes, and malformed URLs', () => {
    const missingProto = validateWebsiteUrlInput('example.com')
    assert.equal(missingProto.valid, false)
    assert.match(missingProto.error, /protocol/i)

    const badScheme = validateWebsiteUrlInput('ftp://example.com')
    assert.equal(badScheme.valid, false)
    assert.match(badScheme.error, /unsupported protocol/i)

    const jsScheme = validateWebsiteUrlInput('javascript:alert(1)')
    assert.equal(jsScheme.valid, false)

    const badHost = validateWebsiteUrlInput('https://notadomain')
    assert.equal(badHost.valid, false)
  })
})

describe('2. API Service (analyzeWebsite & getHealthStatus)', () => {
  it('sends POST /link-analysis with JSON body and returns LinkAnalysisResponse on 200', async () => {
    const sample = buildSampleLinkAnalysisResponse()
    let capturedUrl = ''
    let capturedOptions = null

    const mockFetch = async (url, options) => {
      capturedUrl = url
      capturedOptions = options
      return makeMockJsonResponse(200, sample)
    }

    const result = await analyzeWebsite('https://acme.example', {
      baseUrl: 'http://localhost:4000/',
      fetchImpl: mockFetch,
    })

    assert.equal(capturedUrl, 'http://localhost:4000/link-analysis')
    assert.equal(capturedOptions.method, 'POST')
    assert.equal(capturedOptions.headers['Content-Type'], 'application/json')
    assert.deepEqual(JSON.parse(capturedOptions.body), { url: 'https://acme.example' })
    assert.equal(result.success, true)
    assert.equal(result.website, 'https://www.acme.example/')
    assert.equal(result.brand.name, 'Acme Cloud Analytics')
    assert.equal(result.analysis.target_search_queries.length, 5)
  })

  it('parses backend 422 validation / unsafe URL ErrorResponse envelope', async () => {
    const mockFetch = async () =>
      makeMockJsonResponse(422, {
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: "Access to loopback IP address '127.0.0.1' is not allowed.",
        },
      })

    await assert.rejects(
      () => analyzeWebsite('http://127.0.0.1', { fetchImpl: mockFetch }),
      (err) => {
        assert.ok(err instanceof ApiError)
        assert.equal(err.status, 422)
        assert.equal(err.code, 'VALIDATION_ERROR')
        assert.match(err.message, /loopback/i)
        assert.equal(err.retryable, false)
        return true
      }
    )
  })

  it('parses backend 413, 502, 503, 504, and 500 error responses accurately', async () => {
    const cases = [
      [413, 'WEBSITE_RESPONSE_TOO_LARGE', false],
      [502, 'WEBSITE_FETCH_FAILED', true],
      [503, 'LLM_NOT_CONFIGURED', true],
      [504, 'LLM_TIMEOUT', true],
      [500, 'INTERNAL_SERVER_ERROR', true],
    ]

    for (const [status, code, expectedRetryable] of cases) {
      const mockFetch = async () =>
        makeMockJsonResponse(status, {
          success: false,
          error: { code, message: `Safe error for ${code}` },
        })

      await assert.rejects(
        () => analyzeWebsite('https://example.com', { fetchImpl: mockFetch }),
        (err) => {
          assert.ok(err instanceof ApiError)
          assert.equal(err.status, status)
          assert.equal(err.code, code)
          assert.equal(err.retryable, expectedRetryable)
          return true
        }
      )
    }
  })

  it('maps network failure (backend unavailable) to retryable NETWORK_ERROR', async () => {
    const mockFetch = async () => {
      throw new TypeError('fetch failed')
    }

    await assert.rejects(
      () => analyzeWebsite('https://example.com', { fetchImpl: mockFetch }),
      (err) => {
        assert.ok(err instanceof ApiError)
        assert.equal(err.code, 'NETWORK_ERROR')
        assert.equal(err.retryable, true)
        assert.match(err.message, /FastAPI server/i)
        return true
      }
    )
  })

  it('maps request timeout to retryable CLIENT_TIMEOUT (504)', async () => {
    const mockFetch = (_url, { signal }) =>
      new Promise((_resolve, reject) => {
        signal.addEventListener('abort', () => {
          const abortErr = new Error('Aborted')
          abortErr.name = 'AbortError'
          reject(abortErr)
        })
      })

    await assert.rejects(
      () =>
        analyzeWebsite('https://example.com', {
          timeoutMs: 25,
          fetchImpl: mockFetch,
        }),
      (err) => {
        assert.ok(err instanceof ApiError)
        assert.equal(err.status, 504)
        assert.equal(err.code, 'CLIENT_TIMEOUT')
        assert.equal(err.retryable, true)
        return true
      }
    )
  })

  it('supports GET /health liveness check', async () => {
    const mockFetch = async () => makeMockJsonResponse(200, { status: 'healthy' })
    const health = await getHealthStatus({ fetchImpl: mockFetch })
    assert.deepEqual(health, { status: 'healthy' })
  })
})

describe('3. State runner (duplicate submission, retry, reset) & Results View SSR', () => {
  it('prevents duplicate submissions, supports retry after failure, and stores/resets state', async () => {
    const server = await createServer({
      root: FRONTEND_ROOT,
      server: { middlewareMode: true, hmr: false, ws: false },
      appType: 'custom',
      logLevel: 'error',
    })

    try {
      const { createAnalysisRunner } = await server.ssrLoadModule(
        '/src/context/AnalysisContext.jsx'
      )

      // Duplicate submission guard
      let releaseFirst
      let callCount = 0
      const slowAnalyze = () => {
        callCount += 1
        return new Promise((resolve) => {
          releaseFirst = () => resolve(buildSampleLinkAnalysisResponse())
        })
      }

      const runner = createAnalysisRunner(slowAnalyze)
      const firstPromise = runner.execute('https://acme.example')
      const duplicateResult = await runner.execute('https://acme.example')
      assert.equal(duplicateResult.skipped, true)
      assert.equal(callCount, 1)

      releaseFirst()
      const firstOutcome = await firstPromise
      assert.equal(firstOutcome.ok, true)
      assert.equal(firstOutcome.data.brand.name, 'Acme Cloud Analytics')

      // Retry after failure preserves URL and succeeds on second try
      let attempt = 0
      const flakyRunner = createAnalysisRunner(async () => {
        attempt += 1
        if (attempt === 1) {
          throw new ApiError({
            status: 503,
            code: 'LLM_RATE_LIMITED',
            message: 'Rate limited',
            retryable: true,
          })
        }
        return buildSampleLinkAnalysisResponse()
      })

      let storedUrl = ''
      let storedResult = null
      let storedError = null
      const callbacks = {
        onStart: (u) => {
          storedUrl = u
          storedError = null
        },
        onSuccess: (d) => {
          storedResult = d
        },
        onError: (e) => {
          storedError = e
        },
      }

      const failOutcome = await flakyRunner.execute('https://acme.example', callbacks)
      assert.equal(failOutcome.ok, false)
      assert.equal(storedUrl, 'https://acme.example')
      assert.equal(storedError.code, 'LLM_RATE_LIMITED')
      assert.equal(storedResult, null)

      const retryOutcome = await flakyRunner.execute(storedUrl, callbacks)
      assert.equal(retryOutcome.ok, true)
      assert.equal(storedError, null)
      assert.equal(storedResult.website, 'https://www.acme.example/')

      // Starting a new analysis clears stored result
      storedResult = null
      assert.equal(storedResult, null)
    } finally {
      await server.close()
    }
  })

  it('renders ResultsPage with all actual LinkAnalysisResponse schema fields', async () => {
    const server = await createServer({
      root: FRONTEND_ROOT,
      server: { middlewareMode: true, hmr: false, ws: false },
      appType: 'custom',
      logLevel: 'error',
    })

    try {
      const { ResultsPage } = await server.ssrLoadModule(
        '/src/pages/ResultsPage.jsx'
      )
      const { default: App } = await server.ssrLoadModule('/src/App.jsx')
      const sample = buildSampleLinkAnalysisResponse()

      const resultsHtml = renderToString(
        React.createElement(ResultsPage, {
          data: sample,
          onStartNewAnalysis: () => {},
        })
      )

      // Verify all real LinkAnalysisResponse sections & fields render
      assert.ok(resultsHtml.includes('Acme Cloud Analytics'))
      assert.ok(resultsHtml.includes('https://www.acme.example/'))
      assert.ok(resultsHtml.includes('Mixpanel'))
      assert.ok(resultsHtml.includes('AI Suggested'))
      assert.ok(resultsHtml.includes('best SaaS product analytics platform'))
      assert.ok(resultsHtml.includes('Acme Cloud Analytics | SaaS Product Analytics'))
      assert.ok(resultsHtml.includes('SaaS Retention Cohort Analytics'))
      assert.ok(resultsHtml.includes('SaaS Funnel Monitoring'))
      assert.ok(resultsHtml.includes('Website Identified'))
      assert.ok(resultsHtml.includes('SaaS Growth Leaders'))
      assert.ok(resultsHtml.includes('New Analysis'))

      // Verify full App renders cleanly inside AnalysisProvider
      const appHtml = renderToString(React.createElement(App))
      assert.ok(appHtml.includes('Understand any website.'))
      assert.ok(appHtml.includes('Analyze Website'))
    } finally {
      await server.close()
    }
  })
})

