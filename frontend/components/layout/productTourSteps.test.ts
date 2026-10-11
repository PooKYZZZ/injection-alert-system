import { describe, expect, it } from 'vitest'

import { getProductTourDefinition } from './productTourSteps'

describe('product tour definitions', () => {
  it.each([
    ['/dashboard', 'dashboard', 'dashboard-overview'],
    ['/traffic-history', 'traffic-history', 'history-filters'],
    ['/alerts', 'traffic-history', 'history-filters'],
    ['/user-management', 'user-management', 'user-management-overview'],
  ])('selects the %s tour for %s', (pathname, tourId, firstTarget) => {
    const tour = getProductTourDefinition(pathname)

    expect(tour.id).toBe(tourId)
    expect(tour.steps[0]?.target).toBe(firstTarget)
  })

  it('keeps the general guide available outside supported page tours', () => {
    const tour = getProductTourDefinition('/settings')

    expect(tour.id).toBe('general')
    expect(tour.steps[0]?.target).toBeUndefined()
  })
})
