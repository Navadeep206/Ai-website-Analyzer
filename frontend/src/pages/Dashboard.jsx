import React, { useEffect, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Briefcase,
  FileText,
  Globe,
  Loader2,
  RotateCcw,
  Search,
  ShieldCheck,
  Sparkles,
  Target,
  TrendingUp,
  Users,
  X,
} from 'lucide-react'
import { AnalysisLoadingState } from '../components/analysis/AnalysisLoadingState'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { useAnalysis } from '../context/AnalysisContext'
import { validateWebsiteUrlInput } from '../utils/urlValidation'

const SAMPLE_URLS = [
  'https://example.com',
  'https://stripe.com',
  'https://linear.app',
]

const ANALYSIS_MODULES = [
  {
    title: 'Competitor vs. Brand Analysis',
    description:
      'Brand overview, market positioning, strengths, and relevant AI-suggested competitors with clear similarity reasoning.',
    icon: Target,
  },
  {
    title: 'Target Search Queries',
    description:
      'Five unique, intent-mapped discovery queries tailored across Google, LinkedIn, X, Instagram, and Facebook.',
    icon: Search,
  },
  {
    title: 'SEO Improvement Plan',
    description:
      'Keyword recommendations, optimized title & meta description, supporting content ideas, and observed on-page issues.',
    icon: TrendingUp,
  },
  {
    title: 'Top Five Services',
    description:
      'Prioritized website-identified offerings with supporting page evidence alongside clearly labeled AI inferences.',
    icon: Briefcase,
  },
  {
    title: 'Target Audience Profiles',
    description:
      'Structured customer segments, industries, needs, pain points, and marketing recommendations grounded in page copy.',
    icon: Users,
  },
]

const PIPELINE_STEPS = [
  {
    step: '01',
    title: 'Validate & Protect',
    detail: 'URL syntax, protocol, DNS, redirect, and SSRF security checks.',
  },
  {
    step: '02',
    title: 'Extract & Clean',
    detail: 'Bounded HTML parsing of titles, metadata, headings, links, and prose.',
  },
  {
    step: '03',
    title: 'Structured AI Report',
    detail: 'Schema-validated 5-section output separating facts from inferences.',
  },
]

export function Dashboard({ onSelectView, onAnalysisComplete }) {
  const {
    submittedUrl,
    result,
    isLoading,
    error,
    runAnalysis,
    retryAnalysis,
    cancelAnalysis,
    clearError,
  } = useAnalysis()

  const [url, setUrl] = useState(submittedUrl || '')
  const [validationError, setValidationError] = useState('')

  // Keep local input synced when returning from a failed request so URL is preserved
  useEffect(() => {
    if (submittedUrl && !url) {
      setUrl(submittedUrl)
    }
  }, [submittedUrl])

  const handleSubmit = async (event) => {
    event.preventDefault()
    if (isLoading) return

    const check = validateWebsiteUrlInput(url)
    if (!check.valid) {
      setValidationError(check.error)
      clearError()
      return
    }

    setValidationError('')
    const outcome = await runAnalysis(check.normalizedUrl)
    if (outcome.ok) {
      onAnalysisComplete?.()
    }
  }

  const handleRetry = async () => {
    if (isLoading) return
    setValidationError('')
    const outcome = await retryAnalysis()
    if (outcome.ok) {
      onAnalysisComplete?.()
    }
  }

  const handleSampleSelect = (sampleUrl) => {
    if (isLoading) return
    setUrl(sampleUrl)
    setValidationError('')
    clearError()
  }

  const handleClear = () => {
    if (isLoading) return
    setUrl('')
    setValidationError('')
    clearError()
  }

  return (
    <div className="sitelens-hero-wash">
      <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6 sm:py-14 lg:px-8">
        {/* Hero section */}
        <section className="mx-auto max-w-2xl text-center">
          <div className="flex justify-center">
            <Badge tone="indigo">
              <Sparkles className="h-3 w-3" aria-hidden="true" />
              AI Website Intelligence
            </Badge>
          </div>

          <h2 className="mt-5 text-3xl font-semibold tracking-[-0.025em] text-slate-900 sm:text-4xl sm:leading-[1.15]">
            Understand any website.
            <br />
            <span className="text-indigo-600">Discover what to improve.</span>
          </h2>

          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-slate-600">
            AI-powered insights into your brand, competitors, SEO strategy,
            services, and audience.
          </p>
        </section>

        {/* Primary URL submission card */}
        <section
          className="mx-auto mt-8 max-w-2xl"
          aria-label="Website URL analysis input"
        >
          <Card className="p-4 sm:p-5">
            <form onSubmit={handleSubmit} noValidate>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
                <Input
                  id="website-url-input"
                  type="url"
                  name="url"
                  value={url}
                  disabled={isLoading}
                  onChange={(event) => {
                    setUrl(event.target.value)
                    if (validationError) setValidationError('')
                    if (error) clearError()
                  }}
                  leadingIcon={Globe}
                  placeholder="https://example.com"
                  aria-label="Website URL to analyze"
                  error={validationError}
                  trailingAction={
                    url && !isLoading ? (
                      <button
                        type="button"
                        onClick={handleClear}
                        className="inline-flex h-7 w-7 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                        aria-label="Clear URL input"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    ) : null
                  }
                />

                <Button
                  type="submit"
                  size="lg"
                  disabled={isLoading}
                  className="w-full shrink-0 sm:w-auto"
                >
                  {isLoading ? (
                    <>
                      <Loader2
                        className="h-4 w-4 animate-spin"
                        aria-hidden="true"
                      />
                      Analyzing...
                    </>
                  ) : (
                    <>
                      Analyze Website
                      <ArrowRight className="h-4 w-4" aria-hidden="true" />
                    </>
                  )}
                </Button>
              </div>

              {/* Sample URL helpers */}
              <div className="mt-3.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3">
                <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                  <span>Try an example:</span>
                  {SAMPLE_URLS.map((sample) => (
                    <button
                      key={sample}
                      type="button"
                      disabled={isLoading}
                      onClick={() => handleSampleSelect(sample)}
                      className="rounded-md border border-slate-200/80 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-200 hover:bg-indigo-50/70 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                    >
                      {sample.replace('https://', '')}
                    </button>
                  ))}
                </div>

                <span className="inline-flex items-center gap-1 text-[11px] text-slate-400">
                  <ShieldCheck
                    className="h-3.5 w-3.5 text-slate-400"
                    aria-hidden="true"
                  />
                  Validated server-side for SSRF safety
                </span>
              </div>
            </form>

            {/* Backend / Network Warning vs. Error Alert */}
            {error && !isLoading && (() => {
              const isWarning = error.status === 422 || error.status === 413
              const StatusIcon = isWarning ? AlertTriangle : AlertCircle

              return (
                <div
                  role="alert"
                  aria-live="assertive"
                  className={[
                    'mt-4 rounded-lg border p-3.5 text-xs',
                    isWarning
                      ? 'border-amber-200 bg-amber-50/80 text-amber-950'
                      : 'border-rose-200 bg-rose-50/80 text-rose-900',
                  ].join(' ')}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-2.5 min-w-0">
                      <StatusIcon
                        className={[
                          'mt-0.5 h-4 w-4 shrink-0',
                          isWarning ? 'text-amber-600' : 'text-rose-600',
                        ].join(' ')}
                        aria-hidden="true"
                      />
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-semibold">
                            {isWarning ? 'Check submitted URL' : 'Analysis failed'}
                          </span>
                          <span
                            className={[
                              'rounded px-1.5 py-0.5 font-mono text-[10px] font-medium',
                              isWarning
                                ? 'bg-amber-100 text-amber-900'
                                : 'bg-rose-100 text-rose-800',
                            ].join(' ')}
                          >
                            {error.code}
                          </span>
                        </div>
                        <p
                          className={[
                            'mt-1 leading-relaxed break-words',
                            isWarning ? 'text-amber-900' : 'text-rose-800',
                          ].join(' ')}
                        >
                          {error.message}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={clearError}
                      className={[
                        'rounded p-0.5 shrink-0',
                        isWarning
                          ? 'text-amber-600 hover:bg-amber-100 hover:text-amber-900'
                          : 'text-rose-500 hover:bg-rose-100 hover:text-rose-800',
                      ].join(' ')}
                      aria-label="Dismiss error"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>

                  {error.retryable && (
                    <div className="mt-3 flex items-center gap-2 pl-6">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={handleRetry}
                      >
                        <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                        Retry Analysis
                      </Button>
                    </div>
                  )}
                </div>
              )
            })()}
          </Card>

          {/* Polished Loading State */}
          {isLoading && (
            <AnalysisLoadingState
              url={submittedUrl || url}
              onCancel={cancelAnalysis}
            />
          )}

          {/* Quick link back to current session result if already loaded */}
          {result && !isLoading && (
            <div className="mt-4 flex flex-col gap-3 rounded-xl border border-indigo-200/80 bg-indigo-50/50 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-2.5 min-w-0">
                <FileText
                  className="h-4 w-4 shrink-0 text-indigo-600"
                  aria-hidden="true"
                />
                <p className="truncate text-xs text-slate-700">
                  Latest report ready:{' '}
                  <span className="font-semibold text-slate-900">
                    {result.brand?.name}
                  </span>{' '}
                  <span className="text-slate-500">({result.website})</span>
                </p>
              </div>
              <Button
                variant="subtle"
                size="sm"
                onClick={() => onSelectView('results')}
                className="self-start sm:self-auto shrink-0"
              >
                View Report
                <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </div>
          )}
        </section>

        {/* Empty state before analysis */}
        <section className="mt-12" aria-labelledby="empty-state-heading">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end">
            <div>
              <h3
                id="empty-state-heading"
                className="text-sm font-semibold tracking-tight text-slate-900"
              >
                Structured 5-Section Website Report
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                Enter any public HTTP or HTTPS URL above to generate a validated
                breakdown across all five intelligence modules.
              </p>
            </div>
            <Badge tone="neutral">
              {result ? 'Report available' : 'No analysis run yet'}
            </Badge>
          </div>

          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {ANALYSIS_MODULES.map((module) => {
              const Icon = module.icon
              return (
                <Card key={module.title} hover>
                  <CardHeader>
                    <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-lg border border-indigo-100 bg-indigo-50/70 text-indigo-600">
                      <Icon className="h-4 w-4" aria-hidden="true" />
                    </div>
                    <CardTitle>{module.title}</CardTitle>
                    <CardDescription>{module.description}</CardDescription>
                  </CardHeader>
                </Card>
              )
            })}

            <Card className="border-dashed border-slate-300/90 bg-slate-50/60 shadow-none">
              <CardHeader>
                <CardTitle className="text-slate-800">How It Works</CardTitle>
                <CardDescription>
                  Built on verified extraction and schema-validated Gemini analysis.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {PIPELINE_STEPS.map((item) => (
                  <div key={item.step} className="flex items-start gap-2.5">
                    <span className="mt-0.5 inline-flex h-5 w-6 shrink-0 items-center justify-center rounded bg-white text-[10px] font-semibold text-indigo-600 ring-1 ring-slate-200">
                      {item.step}
                    </span>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-800">
                        {item.title}
                      </p>
                      <p className="text-[11px] leading-relaxed text-slate-500">
                        {item.detail}
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  )
}
