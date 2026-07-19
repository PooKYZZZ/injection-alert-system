import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { alertKeys } from '@/features/alerts/queries'
import { statsKeys } from '@/features/stats/queries'
import { AlertStreamSync } from './AlertStreamSync'

class FakeEventSource {
  static instances: FakeEventSource[] = []
  readonly listeners = new Map<string, Set<EventListener>>()
  close = vi.fn()

  constructor(readonly url: string) {
    FakeEventSource.instances.push(this)
  }

  addEventListener(type: string, listener: EventListener) {
    const listeners = this.listeners.get(type) ?? new Set<EventListener>()
    listeners.add(listener)
    this.listeners.set(type, listeners)
  }

  removeEventListener(type: string, listener: EventListener) {
    this.listeners.get(type)?.delete(listener)
  }

  emit(type: string) {
    this.listeners.get(type)?.forEach((listener) => listener(new Event(type)))
  }
}

describe('AlertStreamSync', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    FakeEventSource.instances = []
    vi.stubGlobal('EventSource', FakeEventSource)
  })

  afterEach(() => {
    cleanup()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('uses one stream and coalesces alert/open invalidations', async () => {
    const queryClient = new QueryClient()
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries').mockResolvedValue()

    const view = render(
      <QueryClientProvider client={queryClient}>
        <AlertStreamSync />
      </QueryClientProvider>
    )

    expect(FakeEventSource.instances).toHaveLength(1)
    expect(FakeEventSource.instances[0].url).toBe('/api/alerts/stream')

    act(() => {
      FakeEventSource.instances[0].emit('open')
      FakeEventSource.instances[0].emit('alert.created')
      FakeEventSource.instances[0].emit('alert.created')
      vi.advanceTimersByTime(200)
    })

    expect(invalidate).toHaveBeenCalledTimes(2)
    expect(invalidate).toHaveBeenCalledWith({ queryKey: alertKeys.all })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: statsKeys.all })

    view.unmount()
    expect(FakeEventSource.instances[0].close).toHaveBeenCalledOnce()
  })

  it('does not create a manual replacement stream after an error', () => {
    const queryClient = new QueryClient()
    render(
      <QueryClientProvider client={queryClient}>
        <AlertStreamSync />
      </QueryClientProvider>
    )

    act(() => FakeEventSource.instances[0].emit('error'))

    expect(FakeEventSource.instances).toHaveLength(1)
  })
})
