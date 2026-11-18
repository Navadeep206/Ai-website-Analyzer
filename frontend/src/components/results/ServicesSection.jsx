import React from 'react'
import { Briefcase } from 'lucide-react'
import { Card, CardContent, CardHeader } from '../ui/Card'
import { SectionHeader } from './SectionHeader'
import { ServiceCard } from './ServiceCard'

export function ServicesSection({ services }) {
  const list = Array.isArray(services) ? services : []
  const websiteCount = list.filter(
    (s) => s?.source_type === 'website_identified'
  ).length
  const inferredCount = list.filter(
    (s) => s?.source_type === 'ai_inferred'
  ).length

  const summaryBadge =
    list.length > 0
      ? `${websiteCount} website · ${inferredCount} inferred`
      : '0 services'

  return (
    <section id="section-services" aria-labelledby="heading-services">
      <Card>
        <CardHeader className="p-5 sm:p-6 pb-4">
          <SectionHeader
            id="heading-services"
            icon={Briefcase}
            title="Top Services"
            description="Core offerings explicitly identified on the website alongside clearly labeled AI-inferred service suggestions."
            badgeText={summaryBadge}
          />
        </CardHeader>

        <CardContent className="px-5 pb-5 sm:px-6 sm:pb-6">
          {list.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2">
              {list.map((service, idx) => (
                <ServiceCard
                  key={`${service?.service_name || 'service'}-${idx}`}
                  service={service}
                  index={idx}
                />
              ))}
            </div>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 px-6 py-8 text-center">
              <p className="text-sm font-medium text-slate-700">
                No services were identified from this website
              </p>
              <p className="mt-1 text-xs text-slate-500">
                The page may not contain enough service detail for reliable extraction.
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  )
}

