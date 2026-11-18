import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Stores a temporary UI feedback value (e.g., copied / exported state) and
 * resets it automatically after durationMs with unmount cleanup.
 */
export function useTransientFlag(initialValue = false, durationMs = 2000) {
  const [value, setValue] = useState(initialValue)
  const timerRef = useRef(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  useEffect(() => clearTimer, [clearTimer])

  const trigger = useCallback(
    (nextValue = true) => {
      clearTimer()
      setValue(nextValue)
      timerRef.current = setTimeout(() => {
        setValue(initialValue)
        timerRef.current = null
      }, durationMs)
    },
    [clearTimer, durationMs, initialValue]
  )

  return [value, trigger]
}

