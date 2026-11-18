import React from 'react'
import { Check, Copy, Search } from 'lucide-react'
import { useTransientFlag } from '../../hooks/useTransientFlag'
import { Button } from '../ui/Button'
import { Card, CardContent, CardHeader } from '../ui/Card'
import { SearchQueryCard } from './SearchQueryCard'
import { SectionHeader } from './SectionHeader'
import {
  copyTextToClipboard,
  formatAllQueriesForCopy,
} from '../../utils/resultsHelpers'

export function SearchQueriesSection({
  queries,
  onCopy = copyTextToClipboard,
}) {
  const [copiedAll, triggerCopiedAll] = useTransientFlag(false, 2000)
  const queryList = Array.isArray(queries) ? queries : []

  const handleCopyAll = async () => {
    const formatted = formatAllQueriesForCopy(queryList)
    if (!formatted) return
    const ok = await onCopy(formatted)
    if (ok) {
      triggerCopiedAll(true)
    }
  }

  return (
    <section id="section-queries" aria-labelledby="heading-queries">
      <Card>
        <CardHeader className="p-5 sm:p-6 pb-4">
          <SectionHeader
            id="heading-queries"
            icon={Search}
            title="Target Search Queries"
            description="Five business-relevant discovery queries mapped by search intent and platform."
            badgeText={`${queryList.length} ${
              queryList.length === 1 ? 'query' : 'queries'
            }`}
            action={
              queryList.length > 0 ? (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleCopyAll}
                  aria-label="Copy all search queries"
                >
                  {copiedAll ? (
                    <>
                      <Check
                        className="h-3.5 w-3.5 text-emerald-600"
                        aria-hidden="true"
                      />
                      <span className="text-emerald-700">Copied All</span>
                    </>
                  ) : (
                    <>
                      <Copy className="h-3.5 w-3.5" aria-hidden="true" />
                      Copy All Queries
                    </>
                  )}
                </Button>
              ) : null
            }
          />
        </CardHeader>

        <CardContent className="space-y-3 px-5 pb-5 sm:px-6 sm:pb-6">
          {queryList.length > 0 ? (
            queryList.map((item, idx) => (
              <SearchQueryCard
                key={`${item?.query || 'query'}-${idx}`}
                item={item}
                index={idx}
                onCopy={onCopy}
              />
            ))
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-6 py-8 text-center">
              <p className="text-sm font-medium text-slate-700">
                No target search queries returned
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  )
}

