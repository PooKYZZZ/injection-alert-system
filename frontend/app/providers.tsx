'use client'

import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import SignInToast from '@/components/SignInToast'
import { alertKeys } from '@/features/alerts/queries'

export function Providers({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            gcTime: 2 * 60 * 1000,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      <SignInToast />
      {/* Invalidate alerts queries when an action retry succeeds from the SignInToast */}
      <InvalidateListener />
      {process.env.NODE_ENV === 'development' && <ReactQueryDevtools />}
    </QueryClientProvider>
  )
}

function InvalidateListener() {
  const queryClient = useQueryClient()

  useEffect(() => {
    function onSuccess(event: Event) {
      const customEvent = event as CustomEvent<{ id?: string }>
      void queryClient.invalidateQueries({ queryKey: alertKeys.all })

      const id = customEvent.detail?.id
      if (id) {
        void queryClient.invalidateQueries({ queryKey: alertKeys.detail(id) })
      }
    }

    window.addEventListener('action-retry-success', onSuccess)
    return () => window.removeEventListener('action-retry-success', onSuccess)
  }, [queryClient])

  return null
}
