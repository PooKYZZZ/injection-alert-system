import { afterEach, describe, expect, it, vi } from 'vitest'

import { themeBootstrapScript } from './theme-bootstrap'

describe('theme bootstrap', () => {
  afterEach(() => {
    vi.restoreAllMocks()
    document.documentElement.removeAttribute('data-theme')
    document.documentElement.style.colorScheme = ''
  })

  it('applies the stored explicit theme', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockReturnValue('light')

    window.eval(themeBootstrapScript)

    expect(document.documentElement).toHaveAttribute('data-theme', 'light')
    expect(document.documentElement.style.colorScheme).toBe('light')
  })

  it('falls back without crashing when storage or matchMedia throws', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('storage unavailable')
    })
    Object.defineProperty(window, 'matchMedia', {
      configurable: true,
      value: vi.fn(() => {
        throw new Error('media query unavailable')
      }),
    })

    expect(() => window.eval(themeBootstrapScript)).not.toThrow()
    expect(document.documentElement).toHaveAttribute('data-theme', 'dark')
  })
})
