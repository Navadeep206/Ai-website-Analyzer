import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { analyzeWebsite, ApiError } from '../services/api'

const AnalysisContext = createContext(null)

/**
 * Pure controller helper used by AnalysisProvider (and directly testable offline).
 *
 * Uses a monotonic requestId guard so cancelled or superseded requests can never
 * overwrite state, clear a newer request's loading flag, or block starting a new
 * analysis immediately after cancellation.
 */
export function createAnalysisRunner(analyzeFn = analyzeWebsite) {
  let activeRequestId = 0
  let inFlight = false
  let activeController = null

  return {
    isInFlight: () => inFlight,
    cancel() {
      activeRequestId += 1
      inFlight = false
      if (activeController) {
        activeController.abort()
        activeController = null
      }
    },
    async execute(url, callbacks = {}) {
      if (inFlight) {
        return { skipped: true, ok: false }
      }

      const requestId = ++activeRequestId
      inFlight = true
      const controller = new AbortController()
      activeController = controller
      const { signal } = controller
      callbacks.onStart?.(url)

      try {
        const data = await analyzeFn(url, { signal })
        if (requestId !== activeRequestId || signal.aborted) {
          callbacks.onCancel?.()
          return { skipped: false, ok: false, cancelled: true }
        }
        callbacks.onSuccess?.(data)
        return { skipped: false, ok: true, data }
      } catch (err) {
        const isApiError =
          err instanceof ApiError ||
          (err && err.name === 'ApiError' && typeof err.code === 'string')

        if (
          requestId !== activeRequestId ||
          signal.aborted ||
          (isApiError && err.code === 'REQUEST_CANCELLED') ||
          (err && err.name === 'AbortError')
        ) {
          callbacks.onCancel?.()
          return { skipped: false, ok: false, cancelled: true }
        }

        const normalizedError = isApiError
          ? {
              status: err.status ?? 0,
              code: err.code,
              message: err.message,
              retryable: Boolean(err.retryable),
            }
          : {
              status: 0,
              code: 'UNEXPECTED_ERROR',
              message: 'An unexpected error occurred while analyzing the website.',
              retryable: true,
            }
        callbacks.onError?.(normalizedError)
        return { skipped: false, ok: false, error: normalizedError }
      } finally {
        if (requestId === activeRequestId) {
          inFlight = false
          activeController = null
          callbacks.onFinish?.()
        }
      }
    },
  }
}

export function AnalysisProvider({ children, analyzeFn = analyzeWebsite }) {
  const [submittedUrl, setSubmittedUrl] = useState('')
  const [result, setResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const runnerRef = useRef(null)
  if (runnerRef.current === null) {
    runnerRef.current = createAnalysisRunner(analyzeFn)
  }

  useEffect(() => {
    return () => {
      runnerRef.current?.cancel()
    }
  }, [])

  const runAnalysis = useCallback(async (url) => {
    const trimmed = typeof url === 'string' ? url.trim() : ''
    if (!trimmed || runnerRef.current.isInFlight()) {
      return { skipped: true, ok: false }
    }

    return runnerRef.current.execute(trimmed, {
      onStart: (targetUrl) => {
        setSubmittedUrl(targetUrl)
        setError(null)
        setIsLoading(true)
      },
      onSuccess: (data) => {
        setResult(data)
        setError(null)
      },
      onError: (normalizedError) => {
        setError(normalizedError)
      },
      onCancel: () => {
        setError(null)
      },
      onFinish: () => {
        setIsLoading(false)
      },
    })
  }, [])

  const retryAnalysis = useCallback(async () => {
    if (!submittedUrl) return { skipped: true, ok: false }
    return runAnalysis(submittedUrl)
  }, [submittedUrl, runAnalysis])

  const cancelAnalysis = useCallback(() => {
    runnerRef.current.cancel()
    setIsLoading(false)
  }, [])

  const resetAnalysis = useCallback(() => {
    runnerRef.current.cancel()
    setIsLoading(false)
    setSubmittedUrl('')
    setResult(null)
    setError(null)
  }, [])

  const clearError = useCallback(() => {
    setError(null)
  }, [])

  return (
    <AnalysisContext.Provider
      value={{
        submittedUrl,
        result,
        isLoading,
        error,
        runAnalysis,
        retryAnalysis,
        cancelAnalysis,
        resetAnalysis,
        clearError,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  )
}

export function useAnalysis() {
  const ctx = useContext(AnalysisContext)
  if (!ctx) {
    throw new Error('useAnalysis must be used within an AnalysisProvider')
  }
  return ctx
}
