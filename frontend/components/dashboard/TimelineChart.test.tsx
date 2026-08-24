import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { buildUniqueDayTicks, buildYAxisMax, dedupeTooltipPayload, TimelineChart } from './TimelineChart'

vi.mock('recharts', async () => {
  const React = await import('react')

  const passthrough =
    (name: string) =>
    function MockChartComponent({
      children,
      ...props
    }: {
      children?: React.ReactNode
      [key: string]: unknown
    }) {
      return (
        <div data-testid={name} data-props={JSON.stringify(props)}>
          {children}
        </div>
      )
    }

  return {
    ResponsiveContainer: passthrough('ResponsiveContainer'),
    ComposedChart: passthrough('ComposedChart'),
    Area: passthrough('Area'),
    Line: passthrough('Line'),
    ReferenceLine: passthrough('ReferenceLine'),
    XAxis: passthrough('XAxis'),
    YAxis: passthrough('YAxis'),
    CartesianGrid: passthrough('CartesianGrid'),
    Tooltip: passthrough('Tooltip'),
  }
})

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

describe('TimelineChart', () => {
  const buckets = [
    {
      bucket_index: 0,
      total_count: 6,
      blocked_count: 3,
      allowed_count: 2,
      throttled_count: 1,
      timestamp_start: new Date(2026, 2, 20, 4, 3),
      timestamp_end: new Date(2026, 2, 20, 11, 3),
      bucket_width_seconds: 7 * 60 * 60,
    },
    {
      bucket_index: 1,
      total_count: 18,
      blocked_count: 10,
      allowed_count: 5,
      throttled_count: 3,
      timestamp_start: new Date(2026, 2, 21, 4, 3),
      timestamp_end: new Date(2026, 2, 21, 11, 3),
      bucket_width_seconds: 7 * 60 * 60,
    },
    {
      bucket_index: 2,
      total_count: 64,
      blocked_count: 40,
      allowed_count: 16,
      throttled_count: 8,
      timestamp_start: new Date(2026, 2, 22, 4, 3),
      timestamp_end: new Date(2026, 2, 22, 11, 3),
      bucket_width_seconds: 7 * 60 * 60,
    },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('uses a lower floor for small windows and rounds up once traffic exceeds the floor', () => {
    expect(buildYAxisMax(0)).toBe(30)
    expect(buildYAxisMax(29)).toBe(30)
    expect(buildYAxisMax(30)).toBe(30)
    expect(buildYAxisMax(31)).toBe(60)
    expect(buildYAxisMax(58)).toBe(60)
    expect(buildYAxisMax(60)).toBe(60)
    expect(buildYAxisMax(61)).toBe(70)
    expect(buildYAxisMax(104)).toBe(110)
  })

  it('falls back to a safe color when css variables resolve empty', () => {
    const getComputedStyleSpy = vi
      .spyOn(window, 'getComputedStyle')
      .mockReturnValue({
        getPropertyValue: () => '',
      } as unknown as CSSStyleDeclaration)

    const { container } = render(<TimelineChart buckets={buckets} timeWindow="24h" />)
    const lineNodes = Array.from(container.querySelectorAll('[data-testid="Line"]'))

    expect(lineNodes).toHaveLength(3)
    for (const node of lineNodes) {
      const props = JSON.parse(node.getAttribute('data-props') ?? '{}') as Record<string, unknown>
      expect(props.stroke).toBe('#888888')
    }

    getComputedStyleSpy.mockRestore()
  })

  it('falls back to a safe color when css lookup throws', () => {
    const getComputedStyleSpy = vi
      .spyOn(window, 'getComputedStyle')
      .mockImplementation(() => {
        throw new Error('styles unavailable')
      })

    const { container } = render(<TimelineChart buckets={buckets} timeWindow="24h" />)
    const lineNodes = Array.from(container.querySelectorAll('[data-testid="Line"]'))

    expect(lineNodes).toHaveLength(3)
    for (const node of lineNodes) {
      const props = JSON.parse(node.getAttribute('data-props') ?? '{}') as Record<string, unknown>
      expect(props.stroke).toBe('#888888')
    }

    getComputedStyleSpy.mockRestore()
  })

  it.each(['1h', '6h', '24h', '7d'] as const)(
    'renders a composed line-over-area chart for %s',
    (timeWindow) => {
      const { container } = render(
        <TimelineChart buckets={buckets} timeWindow={timeWindow} />
      )

      const composedChart = container.querySelector('[data-testid="ComposedChart"]')
      const areaNodes = Array.from(container.querySelectorAll('[data-testid="Area"]'))
      const lineNodes = Array.from(container.querySelectorAll('[data-testid="Line"]'))
      const xAxis = container.querySelector('[data-testid="XAxis"]')
      const yAxis = container.querySelector('[data-testid="YAxis"]')
      const referenceLines = Array.from(container.querySelectorAll('[data-testid="ReferenceLine"]'))

      expect(composedChart).not.toBeNull()
      expect(areaNodes).toHaveLength(3)
      expect(lineNodes).toHaveLength(3)
      expect(referenceLines).toHaveLength(2)

      expect(areaNodes.map((node) => JSON.parse(node.getAttribute('data-props') ?? '{}').dataKey)).toEqual([
        'blocked',
        'throttled',
        'allowed',
      ])
      expect(lineNodes.map((node) => JSON.parse(node.getAttribute('data-props') ?? '{}').dataKey)).toEqual([
        'blocked',
        'throttled',
        'allowed',
      ])

      const xAxisProps = JSON.parse(xAxis?.getAttribute('data-props') ?? '{}') as Record<string, unknown>
      const yAxisProps = JSON.parse(yAxis?.getAttribute('data-props') ?? '{}') as Record<string, unknown>
      expect(yAxisProps.domain).toEqual([0, 60])
      expect(yAxisProps.ticks).toEqual([0, 20, 40, 60])
      if (timeWindow === '7d') {
        expect(Array.isArray(xAxisProps.ticks)).toBe(true)
        expect((xAxisProps.ticks as number[]).length).toBeGreaterThan(0)
        expect(xAxisProps.interval).toBe(0)
        expect(xAxisProps.domain).toEqual(['dataMin', 'dataMax'])
      } else {
        expect(xAxisProps.ticks).toBeUndefined()
      }
    }
  )

  it('starts with a valid responsive-container dimension while ResizeObserver measures the parent', () => {
    const { container } = render(<TimelineChart buckets={buckets} timeWindow="24h" />)
    const responsiveContainer = container.querySelector('[data-testid="ResponsiveContainer"]')
    const props = JSON.parse(responsiveContainer?.getAttribute('data-props') ?? '{}') as Record<string, unknown>

    expect(props).toMatchObject({
      width: '100%',
      height: '100%',
      minHeight: 140,
      initialDimension: { width: 0, height: 140 },
    })
  })

  it('extends the y-axis above 60 when the series data exceeds the baseline', () => {
    const tallBuckets = [
      {
        ...buckets[0],
        blocked_count: 87,
        total_count: 87,
      },
    ]

    const { container } = render(<TimelineChart buckets={tallBuckets} timeWindow="24h" />)
    const yAxis = container.querySelector('[data-testid="YAxis"]')
    const yAxisProps = JSON.parse(yAxis?.getAttribute('data-props') ?? '{}') as Record<string, unknown>

    expect(yAxisProps.domain).toEqual([0, 90])
    expect(yAxisProps.ticks).toEqual([0, 30, 60, 90])
  })

  it('uses set1 neutral border and soft text tokens for chart chrome', () => {
    const { container } = render(<TimelineChart buckets={buckets} timeWindow="24h" />)

    const grid = container.querySelector('[data-testid="CartesianGrid"]')
    const xAxis = container.querySelector('[data-testid="XAxis"]')
    const yAxis = container.querySelector('[data-testid="YAxis"]')

    const gridProps = JSON.parse(grid?.getAttribute('data-props') ?? '{}') as Record<string, unknown>
    const xAxisProps = JSON.parse(xAxis?.getAttribute('data-props') ?? '{}') as Record<string, unknown>
    const yAxisProps = JSON.parse(yAxis?.getAttribute('data-props') ?? '{}') as Record<string, unknown>

    expect(gridProps.stroke).toBe('var(--color-surface-border)')
    expect((xAxisProps.tick as { fill?: string } | undefined)?.fill).toBe('var(--color-text-soft)')
    expect((yAxisProps.tick as { fill?: string } | undefined)?.fill).toBe('var(--color-text-soft)')
  })

  it('deduplicates tooltip payload entries by series key', () => {
    const deduped = dedupeTooltipPayload([
      { dataKey: 'blocked', name: 'blocked', value: 10, color: 'red' },
      { dataKey: 'blocked', name: 'blocked', value: 10, color: 'crimson' },
      { dataKey: 'throttled', name: 'throttled', value: 4, color: 'orange' },
      { dataKey: 'throttled', name: 'throttled', value: 4, color: 'amber' },
      { dataKey: 'allowed', name: 'allowed', value: 1 },
    ])

    expect(deduped.map((entry) => entry.dataKey)).toEqual(['blocked', 'throttled', 'allowed'])
    expect(deduped[0]?.color).toBe('crimson')
    expect(deduped[1]?.color).toBe('amber')
  })

  it('shows the empty state when there are no events', () => {
    const { container, getByText } = render(<TimelineChart buckets={[]} />)

    expect(getByText(/No events in this window/i)).toBeInTheDocument()
    expect(getByText(/Traffic was quiet during this period/i)).toBeInTheDocument()
    expect(container.querySelector('[data-testid="ComposedChart"]')).toBeNull()
  })

  it('provides an accessible text summary of each action series', () => {
    render(<TimelineChart buckets={buckets} timeWindow="24h" />)

    expect(screen.getAllByRole('img', { name: /Request activity for the last 24h/ })[0]).toHaveAttribute(
      'aria-label',
      expect.stringContaining('Blocked 53, Throttled 12, Allowed 23')
    )
  })

  it('shows the pending skeleton while loading', () => {
    const { container } = render(<TimelineChart buckets={[]} isPending />)

    expect(container.querySelectorAll('.animate-skeleton')).toHaveLength(4)
  })
})
