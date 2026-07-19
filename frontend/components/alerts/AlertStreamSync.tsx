'use client'

import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'

import { alertKeys } from '@/features/alerts/queries'
import { statsKeys } from '@/features/stats/queries'

const INVALIDATION_COALESCE_MS = 200

export function AlertStreamSync() {
  const queryClient = useQueryClient()

  useEffect(() => {
    const source = new EventSource('/api/alerts/stream')
    let invalidationTimer: ReturnType<typeof setTimeout> | null = null

    const scheduleCanonicalRefetch = () => {
      if (invalidationTimer !== null) return
      invalidationTimer = setTimeout(() => {
        invalidationTimer = null
        void queryClient.invalidateQueries({ queryKey: alertKeys.all })
        void queryClient.invalidateQueries({ queryKey: statsKeys.all })
      }, INVALIDATION_COALESCE_MS)
    }

    source.addEventListener('open', scheduleCanonicalRefetch)
    source.addEventListener('alert.created', scheduleCanonicalRefetch)

    return () => {
      source.removeEventListener('open', scheduleCanonicalRefetch)
      source.removeEventListener('alert.created', scheduleCanonicalRefetch)
      if (invalidationTimer !== null) clearTimeout(invalidationTimer)
      source.close()
    }
  }, [queryClient])

  return null
}
