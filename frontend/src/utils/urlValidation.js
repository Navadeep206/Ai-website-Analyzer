/**
 * Lightweight frontend URL validation for immediate user feedback.
 *
 * Security note: This validator checks syntax and protocol only. It intentionally
 * does NOT duplicate SSRF, private IP, or DNS protections—the FastAPI backend
 * remains the sole security authority for URL validation.
 */

const ALLOWED_PROTOCOLS = new Set(['http:', 'https:'])
const HAS_SCHEME_RE = /^[a-zA-Z][a-zA-Z\d+\-.]*:/
const CONTROL_OR_SPACE_RE = /[\s\u0000-\u001F\u007F]/

export function validateWebsiteUrlInput(rawUrl) {
  if (typeof rawUrl !== 'string') {
    return { valid: false, normalizedUrl: '', error: 'Please enter a website URL.' }
  }

  const trimmed = rawUrl.trim()
  if (!trimmed) {
    return {
      valid: false,
      normalizedUrl: '',
      error: 'Please enter a website URL (for example, https://example.com).',
    }
  }

  if (CONTROL_OR_SPACE_RE.test(trimmed)) {
    return {
      valid: false,
      normalizedUrl: '',
      error: 'URL cannot contain spaces or control characters.',
    }
  }

  if (!HAS_SCHEME_RE.test(trimmed)) {
    return {
      valid: false,
      normalizedUrl: '',
      error: 'Include the protocol at the start of the URL (e.g., https://example.com).',
    }
  }

  let parsed
  try {
    parsed = new URL(trimmed)
  } catch {
    return {
      valid: false,
      normalizedUrl: '',
      error: 'Please enter a valid website URL (for example, https://example.com).',
    }
  }

  if (!ALLOWED_PROTOCOLS.has(parsed.protocol)) {
    const scheme = parsed.protocol.replace(/:$/, '')
    return {
      valid: false,
      normalizedUrl: '',
      error: `Unsupported protocol "${scheme}". Only http:// and https:// URLs are supported.`,
    }
  }

  if (
    !trimmed.toLowerCase().startsWith(`${parsed.protocol}//`) ||
    !parsed.hostname
  ) {
    return {
      valid: false,
      normalizedUrl: '',
      error: 'Please enter a complete URL with a valid domain name (e.g., https://example.com).',
    }
  }

  const host = parsed.hostname
  const isBracketedIpv6 = host.startsWith('[') && host.endsWith(']')
  if (
    !isBracketedIpv6 &&
    (!host.includes('.') || host.startsWith('.') || host.endsWith('..'))
  ) {
    return {
      valid: false,
      normalizedUrl: '',
      error: 'Please enter a valid domain name (for example, https://example.com).',
    }
  }

  return { valid: true, normalizedUrl: trimmed, error: '' }
}

