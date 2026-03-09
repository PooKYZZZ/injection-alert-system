'use client'

import { useState } from 'react'
import dynamic from 'next/dynamic'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

const ReactQueryDevtools = dynamic(
  () =>
    process.env.NODE_ENV === 'development'
      ? import('@tanstack/react-query-devtools').then((m) => ({ default: m.ReactQueryDevtools }))
      : Promise.resolve({ default: () => null }),
  { ssr: false },
)

export function Providers({ children }: { children: React.ReactNode }) {
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
      <ReactQueryDevtools />
    </QueryClientProvider>
  )
}
