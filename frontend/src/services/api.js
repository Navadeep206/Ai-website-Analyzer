/**
 * Centralized API client for the FastAPI Website Link Analysis backend.
 *
 * Uses native fetch with explicit timeouts and structured ErrorResponse parsing.
 */

const DEFAULT_API_BASE_URL = 'http://localhost:4000'
export const DEFAULT_ANALYSIS_TIMEOUT_MS = 120_000
export const DEFAULT_HEALTH_TIMEOUT_MS = 5_000

const RETRYABLE_HTTP_STATUSES = new Set([502, 503, 504, 500])

const STATUS_FALLBACK_MESSAGES = {
  413: 'The target website response is too large to analyze.',
  422: 'The provided URL could not be validated or does not point to a supported webpage.',
  502: 'Unable to retrieve website content or process the AI analysis response.',
  503: 'The AI analysis service is currently unavailable or not configured. Please try again later.',
  504: 'The analysis request timed out. Please try again.',
  500: 'An unexpected server error occurred. Please try again.',
}

export function getApiBaseUrl() {
  const configured =
    typeof import.meta !== 'undefined' && import.meta.env
      ? import.meta.env.VITE_API_BASE_URL
      : ''
  const base =
    typeof configured === 'string' && configured.trim()
      ? configured.trim()
      : DEFAULT_API_BASE_URL
  return base.replace(/\/+$/, '')
}

export class ApiError extends Error {
  constructor({ status = 0, code = 'UNKNOWN_ERROR', message, retryable = false }) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.retryable = retryable
  }
}

async function safeReadJson(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

function buildErrorFromResponse(status, body) {
  const backendError = body && typeof body === 'object' ? body.error : null
  const code =
    backendError && typeof backendError.code === 'string' && backendError.code.trim()
      ? backendError.code.trim()
      : `HTTP_${status}`

  const message =
    backendError &&
    typeof backendError.message === 'string' &&
    backendError.message.trim()
      ? backendError.message.trim()
      : STATUS_FALLBACK_MESSAGES[status] ||
        'The analysis request could not be completed. Please try again.'

  return new ApiError({
    status,
    code,
    message,
    retryable: RETRYABLE_HTTP_STATUSES.has(status),
  })
}

async function fetchWithTimeout(url, options, timeoutMs, fetchImpl = fetch) {
  const controller = new AbortController()
  const externalSignal = options.signal

  const onExternalAbort = () => controller.abort(externalSignal.reason)
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort(externalSignal.reason)
    } else {
      externalSignal.addEventListener('abort', onExternalAbort, { once: true })
    }
  }

  let timedOut = false
  const timeoutId = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  try {
    return await fetchImpl(url, { ...options, signal: controller.signal })
  } catch (err) {
    if (timedOut) {
      throw new ApiError({
        status: 504,
        code: 'CLIENT_TIMEOUT',
        message:
          'The analysis took longer than expected and timed out. Please try again.',
        retryable: true,
      })
    }
    if (err && err.name === 'AbortError') {
      throw new ApiError({
        status: 0,
        code: 'REQUEST_CANCELLED',
        message: 'The analysis request was cancelled.',
        retryable: true,
      })
    }
    throw new ApiError({
      status: 0,
      code: 'NETWORK_ERROR',
      message:
        'Unable to connect to the analysis backend. Verify the FastAPI server is running and reachable.',
      retryable: true,
    })
  } finally {
    clearTimeout(timeoutId)
    if (externalSignal) {
      externalSignal.removeEventListener('abort', onExternalAbort)
    }
  }
}

/**
 * Submit a website URL to POST /link-analysis and return LinkAnalysisResponse.
 */
export async function analyzeWebsite(
  url,
  {
    signal,
    timeoutMs = DEFAULT_ANALYSIS_TIMEOUT_MS,
    baseUrl = getApiBaseUrl(),
    fetchImpl = fetch,
  } = {}
) {
  const endpoint = `${baseUrl.replace(/\/+$/, '')}/link-analysis`

  const response = await fetchWithTimeout(
    endpoint,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ url }),
      signal,
    },
    timeoutMs,
    fetchImpl
  )

  const body = await safeReadJson(response)

  if (!response.ok) {
    throw buildErrorFromResponse(response.status, body)
  }

  if (
    !body ||
    body.success !== true ||
    typeof body.website !== 'string' ||
    !body.brand ||
    !body.analysis
  ) {
    throw new ApiError({
      status: 502,
      code: 'INVALID_RESPONSE',
      message:
        'The server returned an unexpected response format. Please try again.',
      retryable: true,
    })
  }

  return body
}

/**
 * Check backend liveness via GET /health.
 */
export async function getHealthStatus({
  signal,
  timeoutMs = DEFAULT_HEALTH_TIMEOUT_MS,
  baseUrl = getApiBaseUrl(),
  fetchImpl = fetch,
} = {}) {
  const endpoint = `${baseUrl.replace(/\/+$/, '')}/health`
  const response = await fetchWithTimeout(
    endpoint,
    {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal,
    },
    timeoutMs,
    fetchImpl
  )

  const body = await safeReadJson(response)
  if (!response.ok || !body || body.status !== 'healthy') {
    throw buildErrorFromResponse(response.status || 503, body)
  }
  return body
}

