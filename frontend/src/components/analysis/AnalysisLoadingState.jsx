import React, { useEffect, useState } from 'react'
import { Loader2, X } from 'lucide-react'
import { Button } from '../ui/Button'
import { Card } from '../ui/Card'

export const LOADING_STAGES = [
  'Validating website URL...',
  'Extracting website content...',
  'Understanding the brand and competitors...',
  'Generating SEO recommendations...',
  'Preparing structured insights...',
]

const STAGE_INTERVAL_MS = 2800

export function AnalysisLoadingState({ url, onCancel }) {
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    setStageIndex(0)
    const intervalId = setInterval(() => {
      setStageIndex((prev) => (prev + 1) % LOADING_STAGES.length)
    }, STAGE_INTERVAL_MS)

    return () => clearInterval(intervalId)
  }, [url])

  const currentStage = LOADING_STAGES[stageIndex]

  return (
    <Card
      className="mt-4 border-indigo-200/80 bg-white p-5"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3.5 min-w-0 flex-1">
          <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-indigo-100 bg-indigo-50 text-indigo-600">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="text-sm font-semibold text-slate-900">
                {currentStage}
              </p>
              <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-medium text-indigo-700">
                <span
                  className="h-1.5 w-1.5 rounded-full bg-indigo-600 animate-pulse"
                  aria-hidden="true"
                />
                Running
              </span>
            </div>

            {url && (
              <p className="mt-1 break-all text-xs text-slate-500">
                Target: <span className="font-medium text-slate-700">{url}</span>
              </p>
            )}

            {/* Indeterminate activity bar (never implies a backend stage completed) */}
            <div
              className="mt-3 h-1.5 w-full overflow-hidden rounded-full bg-slate-100"
              aria-hidden="true"
            >
              <div className="sitelens-indeterminate-bar h-full rounded-full bg-indigo-600" />
            </div>

            <p className="mt-2.5 text-[11px] leading-relaxed text-slate-400">
              Status messages are visual estimates while awaiting the API response.
              Website extraction and Gemini analysis typically take several seconds.
            </p>
          </div>
        </div>

        {onCancel && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onCancel}
            className="self-start shrink-0 text-slate-500 hover:text-slate-800"
            aria-label="Cancel analysis request"
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Cancel
          </Button>
        )}
      </div>
    </Card>
  )
}
