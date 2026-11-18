import React from 'react'
import { CheckCircle2, MapPin, Sparkles, Users } from 'lucide-react'
import { Badge } from '../ui/Badge'
import { Card, CardContent, CardHeader } from '../ui/Card'
import { AudienceCard } from './AudienceCard'
import { BulletPanel, TagBucket } from './InsightPrimitives'
import { SectionHeader } from './SectionHeader'
import { asNonEmptyList } from '../../utils/resultsHelpers'

export function AudienceSection({ audience }) {
  if (!audience) {
    return (
      <section id="section-audience" aria-labelledby="heading-audience">
        <Card>
          <CardHeader className="p-5 sm:p-6">
            <SectionHeader
              id="heading-audience"
              icon={Users}
              title="Target Audience Identification"
              description="No target audience insights were returned in this response."
            />
          </CardHeader>
        </Card>
      </section>
    )
  }

  const primary = asNonEmptyList(audience.primary_audience)
  const secondary = asNonEmptyList(audience.secondary_audience)
  const industries = asNonEmptyList(audience.industries)
  const businessTypes = asNonEmptyList(audience.business_types)
  const geoFocus = asNonEmptyList(audience.geographical_focus)
  const marketingSegments = asNonEmptyList(
    audience.recommended_marketing_segments
  )
  const explicitAudiences = asNonEmptyList(
    audience.explicitly_identified_audiences
  )
  const inferredAudiences = asNonEmptyList(audience.inferred_audiences)
  const needs = asNonEmptyList(audience.customer_needs)
  const painPoints = asNonEmptyList(audience.customer_pain_points)
  const interests = asNonEmptyList(audience.potential_interests)
  const profiles = Array.isArray(audience.customer_profiles)
    ? audience.customer_profiles
    : []

  const hasAnyContent =
    primary.length > 0 ||
    secondary.length > 0 ||
    industries.length > 0 ||
    businessTypes.length > 0 ||
    explicitAudiences.length > 0 ||
    inferredAudiences.length > 0 ||
    profiles.length > 0 ||
    needs.length > 0 ||
    painPoints.length > 0

  return (
    <section id="section-audience" aria-labelledby="heading-audience">
      <Card>
        <CardHeader className="p-5 sm:p-6 pb-4">
          <SectionHeader
            id="heading-audience"
            icon={Users}
            title="Target Audience Identification"
            description="Audience segments grounded in website services, explicitly separating on-page mentions from AI inferences."
            badgeText={
              profiles.length > 0
                ? `${profiles.length} ${
                    profiles.length === 1 ? 'profile' : 'profiles'
                  }`
                : undefined
            }
          />
        </CardHeader>

        <CardContent className="space-y-6 px-5 pb-5 sm:px-6 sm:pb-6">
          {!hasAnyContent ? (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-6 py-8 text-center">
              <p className="text-sm font-medium text-slate-700">
                No target audience details were available
              </p>
              <p className="mt-1 text-xs text-slate-500">
                Website content did not provide enough signal to identify audience segments.
              </p>
            </div>
          ) : (
            <>
              {/* Fact vs. Inference split */}
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-emerald-200/70 bg-emerald-50/40 p-4">
                  <div className="mb-2 flex items-center gap-1.5">
                    <CheckCircle2
                      className="h-3.5 w-3.5 text-emerald-600"
                      aria-hidden="true"
                    />
                    <p className="text-xs font-semibold text-emerald-900">
                      Explicitly Identified on Website
                    </p>
                  </div>
                  {explicitAudiences.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {explicitAudiences.map((item, idx) => (
                        <Badge key={`${item}-${idx}`} tone="emerald">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">
                      No audience groups were explicitly named on the webpage.
                    </p>
                  )}
                </div>

                <div className="rounded-xl border border-indigo-200/70 bg-indigo-50/40 p-4">
                  <div className="mb-2 flex items-center gap-1.5">
                    <Sparkles
                      className="h-3.5 w-3.5 text-indigo-600"
                      aria-hidden="true"
                    />
                    <p className="text-xs font-semibold text-indigo-900">
                      AI-Inferred Audiences
                    </p>
                  </div>
                  {inferredAudiences.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {inferredAudiences.map((item, idx) => (
                        <Badge key={`${item}-${idx}`} tone="indigo">
                          {item}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-500">
                      No additional inferred audience segments.
                    </p>
                  )}
                </div>
              </div>

              {/* Taxonomy grid */}
              <div className="grid gap-4 border-t border-slate-100 pt-5 sm:grid-cols-2 lg:grid-cols-3">
                <TagBucket
                  label="Primary Audience"
                  items={primary}
                  tone="indigo"
                />
                <TagBucket
                  label="Secondary Audience"
                  items={secondary}
                  tone="neutral"
                />
                <TagBucket
                  label="Industries"
                  items={industries}
                  tone="subtle"
                />
                <TagBucket
                  label="Business Types"
                  items={businessTypes}
                  tone="subtle"
                />
                <div>
                  <p className="mb-1.5 flex items-center gap-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
                    <MapPin className="h-3 w-3" aria-hidden="true" />
                    Geographical Focus
                  </p>
                  {geoFocus.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {geoFocus.map((geo, idx) => (
                        <Badge key={`${geo}-${idx}`} tone="sky">
                          {geo}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400">
                      Not specified on website
                    </p>
                  )}
                </div>
                <TagBucket
                  label="Marketing Segments"
                  items={marketingSegments}
                  tone="neutral"
                />
              </div>

              {/* Needs, Pain Points, Interests */}
              {(needs.length > 0 ||
                painPoints.length > 0 ||
                interests.length > 0) && (
                <div className="grid gap-3 border-t border-slate-100 pt-5 md:grid-cols-3">
                  <BulletPanel
                    title="Customer Needs"
                    items={needs}
                    dotClass="bg-indigo-500"
                  />
                  <BulletPanel
                    title="Customer Pain Points"
                    items={painPoints}
                    dotClass="bg-amber-400"
                  />
                  <BulletPanel
                    title="Potential Interests"
                    items={interests}
                    dotClass="bg-sky-500"
                  />
                </div>
              )}

              {/* Detailed Customer Profiles */}
              {profiles.length > 0 && (
                <div className="space-y-3 border-t border-slate-100 pt-5">
                  <p className="text-xs font-semibold text-slate-900">
                    Customer Profiles
                  </p>
                  <div className="grid gap-4 md:grid-cols-2">
                    {profiles.map((profile, idx) => (
                      <AudienceCard
                        key={`${profile?.audience_segment || 'profile'}-${idx}`}
                        profile={profile}
                      />
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </section>
  )
}

