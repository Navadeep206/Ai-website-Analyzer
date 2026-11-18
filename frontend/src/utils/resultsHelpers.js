/**
 * Safe formatting, link validation, and clipboard utilities for the Results Dashboard.
 */

export function isSafeExternalUrl(rawUrl) {
  if (typeof rawUrl !== 'string' || !rawUrl.trim()) {
    return false
  }
  try {
    const parsed = new URL(rawUrl.trim())
    return parsed.protocol === 'http:' || parsed.protocol === 'https:'
  } catch {
    return false
  }
}

export async function copyTextToClipboard(text, clipboardImpl) {
  if (typeof text !== 'string' || !text) {
    return false
  }

  const targetClipboard =
    clipboardImpl ||
    (typeof navigator !== 'undefined' ? navigator.clipboard : null)

  if (targetClipboard && typeof targetClipboard.writeText === 'function') {
    try {
      await targetClipboard.writeText(text)
      return true
    } catch {
      return false
    }
  }

  // Fallback for older browser contexts without navigator.clipboard
  if (typeof document !== 'undefined') {
    try {
      const textarea = document.createElement('textarea')
      textarea.value = text
      textarea.setAttribute('readonly', '')
      textarea.style.position = 'fixed'
      textarea.style.opacity = '0'
      document.body.appendChild(textarea)
      textarea.select()
      const copied = document.execCommand('copy')
      document.body.removeChild(textarea)
      return Boolean(copied)
    } catch {
      return false
    }
  }

  return false
}

export function formatAllQueriesForCopy(queries) {
  if (!Array.isArray(queries) || queries.length === 0) {
    return ''
  }
  return queries
    .map((item) => (typeof item?.query === 'string' ? item.query.trim() : ''))
    .filter(Boolean)
    .join('\n')
}

export function getSourceMeta(sourceType) {
  switch (sourceType) {
    case 'website_identified':
      return { label: 'Website Identified', tone: 'emerald', isVerifiedOnSite: true }
    case 'website_mentioned':
      return { label: 'Mentioned on Website', tone: 'emerald', isVerifiedOnSite: true }
    case 'ai_suggested':
      return { label: 'AI Suggested', tone: 'amber', isVerifiedOnSite: false }
    case 'ai_inferred':
      return { label: 'AI Inferred', tone: 'indigo', isVerifiedOnSite: false }
    default:
      return { label: '', tone: 'neutral', isVerifiedOnSite: false }
  }
}

export function getPriorityTone(priority) {
  const normalized = typeof priority === 'string' ? priority.trim().toLowerCase() : ''
  if (normalized === 'high') return 'rose'
  if (normalized === 'medium') return 'amber'
  if (normalized === 'low') return 'neutral'
  return 'neutral'
}

export function getPlatformBadgeStyle(platform) {
  switch (platform) {
    case 'Google':
      return 'sky'
    case 'LinkedIn':
      return 'indigo'
    case 'X':
      return 'neutral'
    case 'Instagram':
      return 'rose'
    case 'Facebook':
      return 'sky'
    default:
      return 'subtle'
  }
}

export function asNonEmptyList(value) {
  if (!Array.isArray(value)) return []
  return value.filter((item) =>
    typeof item === 'string' ? item.trim().length > 0 : Boolean(item)
  )
}

