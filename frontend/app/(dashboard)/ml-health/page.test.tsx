'use client'

import { describe, expect, it, vi } from 'vitest'

const redirectMock = vi.fn()

vi.mock('next/navigation', () => ({
  redirect: redirectMock,
}))

describe('MLHealthPage', () => {
  it('redirects to the dashboard route', async () => {
    const { default: MLHealthPage } = await import('./page')

    MLHealthPage()

    expect(redirectMock).toHaveBeenCalledWith('/dashboard')
  })
})
