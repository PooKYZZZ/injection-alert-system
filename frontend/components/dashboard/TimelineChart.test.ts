import { describe, expect, it } from 'vitest'
import { buildUniqueDayTicks } from './TimelineChart'

function localDayKey(timestampMs: number): string {
  const date = new Date(timestampMs)
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
}

describe('buildUniqueDayTicks', () => {
  it('returns one tick per local day in ascending order', () => {
    const ts = [
      new Date(2026, 2, 16, 1, 5).getTime(),
      new Date(2026, 2, 16, 10, 45).getTime(),
      new Date(2026, 2, 17, 2, 10).getTime(),
      new Date(2026, 2, 17, 22, 55).getTime(),
      new Date(2026, 2, 18, 9, 30).getTime(),
    ]

    const ticks = buildUniqueDayTicks(ts)
    const dayKeys = ticks.map(localDayKey)

    expect(ticks).toHaveLength(3)
    expect(dayKeys).toEqual(['2026-2-16', '2026-2-17', '2026-2-18'])
    expect(ticks[0]).toBeLessThan(ticks[1])
    expect(ticks[1]).toBeLessThan(ticks[2])
  })

  it('deduplicates unsorted input and ignores invalid numbers', () => {
    const day1Late = new Date(2026, 2, 20, 23, 30).getTime()
    const day1Early = new Date(2026, 2, 20, 1, 20).getTime()
    const day2 = new Date(2026, 2, 21, 5, 0).getTime()

    const ticks = buildUniqueDayTicks([
      day2,
      Number.NaN,
      day1Late,
      Number.POSITIVE_INFINITY,
      day1Early,
    ])
    const dayKeys = ticks.map(localDayKey)

    expect(ticks).toHaveLength(2)
    expect(dayKeys).toEqual(['2026-2-20', '2026-2-21'])
    expect(ticks[0]).toBeLessThan(ticks[1])
  })
})
