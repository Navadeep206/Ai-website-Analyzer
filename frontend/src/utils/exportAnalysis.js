/**
 * Safe client-side export utilities for LinkAnalysisResponse (JSON & Markdown).
 *
 * Exports exclusively real fields returned by the backend API without inventing
 * scores, timestamps, or metrics.
 */

import { asNonEmptyList, getSourceMeta } from './resultsHelpers.js'

const MAX_SLUG_LENGTH = 48

export function buildSafeExportFilename(brandName, website, extension) {
  const ext = extension === 'md' ? 'md' : 'json'
  let rawBase = typeof brandName === 'string' && brandName.trim() ? brandName.trim() : ''

  if (!rawBase && typeof website === 'string' && website.trim()) {
    try {
      rawBase = new URL(website.trim()).hostname
    } catch {
      rawBase = 'website'
    }
  }

  const slug = rawBase
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, MAX_SLUG_LENGTH)

  return `sitelens-${slug || 'analysis'}.${ext}`
}

export function serializeAnalysisAsJson(data) {
  if (!data || typeof data !== 'object') {
    return '{}'
  }
  return `${JSON.stringify(data, null, 2)}\n`
}

function mdBullets(items, emptyText = '_None reported._') {
  const list = asNonEmptyList(items)
  if (list.length === 0) return emptyText
  return list.map((item) => `- ${item}`).join('\n')
}

export function serializeAnalysisAsMarkdown(data) {
  if (!data || typeof data !== 'object') {
    return ''
  }

  const website = typeof data.website === 'string' ? data.website : ''
  const brand = data.brand && typeof data.brand === 'object' ? data.brand : {}
  const analysis = data.analysis && typeof data.analysis === 'object' ? data.analysis : {}
  const comp = analysis.competitor_analysis || null
  const queries = Array.isArray(analysis.target_search_queries)
    ? analysis.target_search_queries
    : []
  const seo = analysis.seo_improvements || null
  const services = Array.isArray(analysis.top_services) ? analysis.top_services : []
  const audience = analysis.target_audience || null

  const lines = []
  const brandSource = getSourceMeta(brand.source_type).label

  lines.push(`# ${brand.name || 'Website Analysis Report'}`)
  lines.push('')
  if (website) lines.push(`- **Analyzed Website:** ${website}`)
  if (brand.category) lines.push(`- **Category:** ${brand.category}`)
  if (brandSource) lines.push(`- **Brand Attribution:** ${brandSource}`)
  lines.push('')

  if (brand.summary) {
    lines.push('## Brand Overview')
    lines.push('')
    lines.push(brand.summary)
    lines.push('')
  }

  if (comp) {
    lines.push('## 1. Competitor vs. Brand Analysis')
    lines.push('')
    if (comp.brand_overview) {
      lines.push(`**Brand Overview:** ${comp.brand_overview}`)
      lines.push('')
    }
    if (comp.market_positioning) {
      lines.push(`**Market Positioning:** ${comp.market_positioning}`)
      lines.push('')
    }
    if (comp.limitations) {
      lines.push(`> **Limitations:** ${comp.limitations}`)
      lines.push('')
    }

    lines.push('### Brand Strengths')
    lines.push(mdBullets(comp.brand_strengths))
    lines.push('')
    lines.push('### Competitive Advantages')
    lines.push(mdBullets(comp.competitive_advantages))
    lines.push('')
    lines.push('### Opportunities')
    lines.push(mdBullets(comp.opportunities))
    lines.push('')

    const competitors = Array.isArray(comp.competitors) ? comp.competitors : []
    lines.push(`### Competitors (${competitors.length})`)
    lines.push('')
    if (competitors.length === 0) {
      lines.push('_No competitors were suggested for this website._')
      lines.push('')
    } else {
      for (const c of competitors) {
        const status = getSourceMeta(c?.verification_status).label || 'AI Suggested'
        lines.push(`#### ${c?.name || 'Unnamed Competitor'} (${status})`)
        if (c?.category) lines.push(`- **Category:** ${c.category}`)
        if (c?.overview) lines.push(`- **Overview:** ${c.overview}`)
        if (c?.reason_for_similarity) {
          lines.push(`- **Why Relevant:** ${c.reason_for_similarity}`)
        }
        if (c?.competitive_comparison) {
          lines.push(`- **Comparison:** ${c.competitive_comparison}`)
        }
        const strengths = asNonEmptyList(c?.key_strengths)
        if (strengths.length) {
          lines.push(`- **Key Strengths:** ${strengths.join('; ')}`)
        }
        const weaknesses = asNonEmptyList(c?.potential_weaknesses)
        if (weaknesses.length) {
          lines.push(`- **Potential Weaknesses:** ${weaknesses.join('; ')}`)
        }
        lines.push('')
      }
    }
  }

  lines.push(`## 2. Target Search Queries (${queries.length})`)
  lines.push('')
  if (queries.length === 0) {
    lines.push('_No target search queries returned._')
    lines.push('')
  } else {
    queries.forEach((q, idx) => {
      const platforms = asNonEmptyList(q?.platforms).join(', ')
      lines.push(
        `${idx + 1}. **${q?.query || ''}** — Intent: ${q?.intent || 'N/A'}${
          platforms ? ` | Platforms: ${platforms}` : ''
        }`
      )
      if (q?.business_relevance) lines.push(`   - Relevance: ${q.business_relevance}`)
      if (q?.target_audience) lines.push(`   - Audience: ${q.target_audience}`)
    })
    lines.push('')
  }

  if (seo) {
    lines.push('## 3. SEO Recommendations')
    lines.push('')
    if (seo.recommended_seo_title) {
      lines.push(
        `- **Recommended Title:** ${seo.recommended_seo_title.recommended_title}`
      )
      if (seo.recommended_seo_title.reason) {
        lines.push(`  - Reason: ${seo.recommended_seo_title.reason}`)
      }
    }
    if (seo.recommended_meta_description) {
      lines.push(
        `- **Recommended Meta Description:** ${seo.recommended_meta_description.recommended_meta_description}`
      )
      if (seo.recommended_meta_description.explanation) {
        lines.push(
          `  - Explanation: ${seo.recommended_meta_description.explanation}`
        )
      }
    }
    lines.push('')

    if (seo.keyword_recommendations) {
      const kw = seo.keyword_recommendations
      lines.push('### Keyword Recommendations')
      if (kw.primary_keyword) lines.push(`- **Primary:** ${kw.primary_keyword}`)
      if (asNonEmptyList(kw.secondary_keywords).length) {
        lines.push(`- **Secondary:** ${asNonEmptyList(kw.secondary_keywords).join(', ')}`)
      }
      if (asNonEmptyList(kw.long_tail_keywords).length) {
        lines.push(`- **Long-Tail:** ${asNonEmptyList(kw.long_tail_keywords).join(', ')}`)
      }
      if (asNonEmptyList(kw.related_keywords).length) {
        lines.push(`- **Related:** ${asNonEmptyList(kw.related_keywords).join(', ')}`)
      }
      lines.push('')
    }

    const content = Array.isArray(seo.supporting_content) ? seo.supporting_content : []
    if (content.length > 0) {
      lines.push('### Supporting Content Recommendations')
      for (const item of content) {
        lines.push(
          `- **[${item.priority || 'Medium'} Priority] ${item.content_type || 'Content'}: ${
            item.suggested_title || ''
          }** (Keyword: ${item.target_keyword || 'N/A'}) — ${item.purpose || ''}`
        )
      }
      lines.push('')
    }

    if (seo.seo_issues) {
      lines.push('### Observed On-Page Issues')
      lines.push(mdBullets(seo.seo_issues.observed_issues))
      lines.push('')
      lines.push('### Recommended Improvements')
      lines.push(mdBullets(seo.seo_issues.recommended_improvements))
      lines.push('')
      lines.push('### Potential Technical Audit Items')
      lines.push(mdBullets(seo.seo_issues.potential_technical_audit_items))
      lines.push('')
    }
  }

  lines.push(`## 4. Top Services (${services.length})`)
  lines.push('')
  if (services.length === 0) {
    lines.push('_No services were identified._')
    lines.push('')
  } else {
    services.forEach((s, idx) => {
      const label = getSourceMeta(s?.source_type).label
      lines.push(
        `${idx + 1}. **${s?.service_name || 'Service'}**${label ? ` (${label})` : ''}`
      )
      if (s?.description) lines.push(`   - Description: ${s.description}`)
      if (s?.main_benefit) lines.push(`   - Main Benefit: ${s.main_benefit}`)
      const targetIndustries = asNonEmptyList(s?.target_industry)
      if (targetIndustries.length) {
        lines.push(`   - Target Industries: ${targetIndustries.join(', ')}`)
      }
      const targetCustomers = asNonEmptyList(s?.target_customer)
      if (targetCustomers.length) {
        lines.push(`   - Target Customers: ${targetCustomers.join(', ')}`)
      }
      if (s?.evidence) lines.push(`   - Evidence: "${s.evidence}"`)
    })
    lines.push('')
  }

  if (audience) {
    lines.push('## 5. Target Audience Identification')
    lines.push('')
    lines.push('### Explicitly Identified on Website')
    lines.push(mdBullets(audience.explicitly_identified_audiences))
    lines.push('')
    lines.push('### AI-Inferred Audiences')
    lines.push(mdBullets(audience.inferred_audiences))
    lines.push('')
    if (asNonEmptyList(audience.primary_audience).length) {
      lines.push(`- **Primary Audience:** ${asNonEmptyList(audience.primary_audience).join(', ')}`)
    }
    if (asNonEmptyList(audience.secondary_audience).length) {
      lines.push(`- **Secondary Audience:** ${asNonEmptyList(audience.secondary_audience).join(', ')}`)
    }
    if (asNonEmptyList(audience.industries).length) {
      lines.push(`- **Industries:** ${asNonEmptyList(audience.industries).join(', ')}`)
    }
    if (asNonEmptyList(audience.business_types).length) {
      lines.push(`- **Business Types:** ${asNonEmptyList(audience.business_types).join(', ')}`)
    }
    const geo = asNonEmptyList(audience.geographical_focus)
    lines.push(
      `- **Geographical Focus:** ${geo.length ? geo.join(', ') : 'Not specified on website'}`
    )
    if (asNonEmptyList(audience.recommended_marketing_segments).length) {
      lines.push(
        `- **Recommended Marketing Segments:** ${asNonEmptyList(audience.recommended_marketing_segments).join(', ')}`
      )
    }
    lines.push('')

    const needs = asNonEmptyList(audience.customer_needs)
    if (needs.length) {
      lines.push('### Customer Needs')
      lines.push(mdBullets(needs))
      lines.push('')
    }
    const painPoints = asNonEmptyList(audience.customer_pain_points)
    if (painPoints.length) {
      lines.push('### Customer Pain Points')
      lines.push(mdBullets(painPoints))
      lines.push('')
    }
    const interests = asNonEmptyList(audience.potential_interests)
    if (interests.length) {
      lines.push('### Potential Interests')
      lines.push(mdBullets(interests))
      lines.push('')
    }

    const profiles = Array.isArray(audience.customer_profiles)
      ? audience.customer_profiles
      : []
    if (profiles.length > 0) {
      lines.push(`### Customer Profiles (${profiles.length})`)
      lines.push('')
      for (const profile of profiles) {
        const pSource = getSourceMeta(profile?.source_type).label
        lines.push(
          `#### ${profile?.audience_segment || 'Audience Segment'}${pSource ? ` (${pSource})` : ''}`
        )
        if (profile?.business_type) lines.push(`- **Business Type:** ${profile.business_type}`)
        if (profile?.industry) lines.push(`- **Industry:** ${profile.industry}`)
        const pNeeds = asNonEmptyList(profile?.customer_needs)
        if (pNeeds.length) lines.push(`- **Needs:** ${pNeeds.join('; ')}`)
        const pChallenges = asNonEmptyList(profile?.challenges)
        if (pChallenges.length) lines.push(`- **Challenges:** ${pChallenges.join('; ')}`)
        const pServices = asNonEmptyList(profile?.relevant_services)
        if (pServices.length) lines.push(`- **Relevant Services:** ${pServices.join(', ')}`)
        if (profile?.marketing_recommendation) {
          lines.push(`- **Marketing Recommendation:** ${profile.marketing_recommendation}`)
        }
        lines.push('')
      }
    }
  }

  return `${lines.join('\n').trimEnd()}\n`
}

export function triggerFileDownload(content, filename, mimeType) {
  if (typeof document === 'undefined' || typeof Blob === 'undefined') {
    return false
  }
  try {
    const blob = new Blob([content], { type: mimeType })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    return true
  } catch {
    return false
  }
}

