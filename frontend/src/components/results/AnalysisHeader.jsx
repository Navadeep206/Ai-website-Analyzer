import React from 'react'
import {
  Check,
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  Globe,
  Plus,
} from 'lucide-react'
import { useTransientFlag } from '../../hooks/useTransientFlag'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'
import {
  buildSafeExportFilename,
  serializeAnalysisAsJson,
  serializeAnalysisAsMarkdown,
  triggerFileDownload,
} from '../../utils/exportAnalysis'
import {
  copyTextToClipboard,
  getSourceMeta,
  isSafeExternalUrl,
} from '../../utils/resultsHelpers'

const SECTION_ANCHORS = [
  { id: 'section-overview', label: 'Overview' },
  { id: 'section-competitors', label: 'Competitors' },
  { id: 'section-queries', label: 'Search Queries' },
  { id: 'section-seo', label: 'SEO' },
  { id: 'section-services', label: 'Services' },
  { id: 'section-audience', label: 'Audience' },
]

export function AnalysisHeader({
  data,
  website,
  brand,
  onStartNewAnalysis,
  onCopyUrl = copyTextToClipboard,
}) {
  const [urlCopied, triggerUrlCopied] = useTransientFlag(false, 2000)
  const [exportedFormat, triggerExportedFormat] = useTransientFlag('', 2000)
  const safeLink = isSafeExternalUrl(website)
  const brandSource = getSourceMeta(brand?.source_type)

  const handleCopyUrl = async () => {
    if (!website) return
    const ok = await onCopyUrl(website)
    if (ok) {
      triggerUrlCopied(true)
    }
  }

  const handleExport = (format) => {
    if (!data) return
    const filename = buildSafeExportFilename(brand?.name, website, format)
    const content =
      format === 'md'
        ? serializeAnalysisAsMarkdown(data)
        : serializeAnalysisAsJson(data)
    const mimeType =
      format === 'md'
        ? 'text/markdown;charset=utf-8'
        : 'application/json;charset=utf-8'

    if (triggerFileDownload(content, filename, mimeType)) {
      triggerExportedFormat(format)
    }
  }

  return (
    <div className="space-y-4">
      <Card className="p-5 sm:p-6">
        <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
          <div className="min-w-0 space-y-2.5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge tone="emerald">
                <CheckCircle2 className="h-3 w-3" aria-hidden="true" />
                Analysis Complete
              </Badge>
              {brand?.category && <Badge tone="indigo">{brand.category}</Badge>}
              {brandSource.label && (
                <Badge tone={brandSource.tone}>{brandSource.label}</Badge>
              )}
            </div>

            <h2 className="text-2xl font-semibold tracking-[-0.02em] text-slate-900 sm:text-3xl break-words">
              {brand?.name || 'Website Analysis Report'}
            </h2>

            {website && (
              <div className="flex flex-wrap items-center gap-2 pt-0.5">
                <div className="inline-flex max-w-full items-center gap-1.5 rounded-md border border-slate-200/80 bg-slate-50 px-2.5 py-1 text-xs text-slate-700">
                  <Globe
                    className="h-3.5 w-3.5 shrink-0 text-slate-400"
                    aria-hidden="true"
                  />
                  <span className="break-all font-medium">{website}</span>
                </div>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopyUrl}
                  aria-label="Copy analyzed website URL"
                >
                  {urlCopied ? (
                    <>
                      <Check
                        className="h-3.5 w-3.5 text-emerald-600"
                        aria-hidden="true"
                      />
                      <span className="text-emerald-700">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                      Copy URL
                    </>
                  )}
                </Button>

                {safeLink && (
                  <a
                    href={website}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex h-8 items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-medium text-slate-700 transition-colors hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
                  >
                    Visit Site
                    <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </a>
                )}
              </div>
            )}
          </div>

          <div className="flex flex-wrap shrink-0 items-center gap-2">
            {data && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleExport('json')}
                  aria-label="Download analysis as JSON"
                >
                  {exportedFormat === 'json' ? (
                    <>
                      <Check
                        className="h-3.5 w-3.5 text-emerald-600"
                        aria-hidden="true"
                      />
                      <span className="text-emerald-700">JSON Saved</span>
                    </>
                  ) : (
                    <>
                      <Download className="h-3.5 w-3.5" aria-hidden="true" />
                      Export JSON
                    </>
                  )}
                </Button>

                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleExport('md')}
                  aria-label="Download analysis as Markdown"
                >
                  {exportedFormat === 'md' ? (
                    <>
                      <Check
                        className="h-3.5 w-3.5 text-emerald-600"
                        aria-hidden="true"
                      />
                      <span className="text-emerald-700">Markdown Saved</span>
                    </>
                  ) : (
                    <>
                      <Download className="h-3.5 w-3.5" aria-hidden="true" />
                      Export MD
                    </>
                  )}
                </Button>
              </>
            )}

            <Button variant="primary" size="md" onClick={onStartNewAnalysis}>
              <Plus className="h-4 w-4" aria-hidden="true" />
              New Analysis
            </Button>
          </div>
        </div>

        {/* Section jump links */}
        <nav
          aria-label="Report sections"
          className="mt-5 flex flex-wrap gap-1.5 border-t border-slate-100 pt-4"
        >
          {SECTION_ANCHORS.map((item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className="rounded-md border border-slate-200/80 bg-slate-50/70 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-200 hover:bg-indigo-50/70 hover:text-indigo-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40"
            >
              {item.label}
            </a>
          ))}
        </nav>
      </Card>
    </div>
  )
}
