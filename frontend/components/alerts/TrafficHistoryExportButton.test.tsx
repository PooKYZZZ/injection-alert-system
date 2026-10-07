import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { TrafficHistoryExportButton } from './TrafficHistoryExportButton'

let mockSearchParams = new URLSearchParams()

function addCalendarDays(value: string, days: number): string {
  const date = new Date(`${value}T00:00:00Z`)
  date.setUTCDate(date.getUTCDate() + days)
  return date.toISOString().slice(0, 10)
}

vi.mock('next/navigation', () => ({
  useSearchParams: () => mockSearchParams,
}))

beforeEach(() => {
  mockSearchParams = new URLSearchParams()
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', {
    configurable: true,
    value: function showModal(this: HTMLDialogElement) {
      this.open = true
    },
  })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', {
    configurable: true,
    value: function close(this: HTMLDialogElement) {
      this.open = false
      this.dispatchEvent(new Event('close'))
    },
  })
  vi.stubGlobal('fetch', vi.fn())
  vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:traffic-history-test')
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('TrafficHistoryExportButton', () => {
  it('hides the export control for roles without export permission', () => {
    render(<TrafficHistoryExportButton role="VIEWER" />)

    expect(screen.queryByRole('button', { name: 'Export CSV' })).not.toBeInTheDocument()
  })

  it('submits custom dates with canonical current filters and exposes a download', async () => {
    const user = userEvent.setup()
    mockSearchParams = new URLSearchParams(
      'window=7d&page=4&search=SQLi&action=BLOCKED&include_normal=true&confidence_level=HIGH&confidence_level=MEDIUM'
    )
    render(<TrafficHistoryExportButton role="ANALYST" />)
    await user.click(screen.getByRole('button', { name: 'Export CSV' }))
    expect(screen.getByRole('dialog')).toHaveTextContent(
      'This replaces the Time Window preset'
    )
    const endDate = (screen.getByLabelText('End date') as HTMLInputElement).value
    const startDate = addCalendarDays(endDate, -2)
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response('traffic_log_id,timestamp_utc\r\n1,2026-10-01T00:00:00Z\r\n', {
        status: 200,
        headers: {
          'Content-Type': 'text/csv; charset=utf-8',
          'Content-Disposition': `attachment; filename="traffic-history_${startDate}_to_${endDate}.csv"`,
        },
      })
    )
    fireEvent.change(screen.getByLabelText('Start date'), { target: { value: startDate } })
    fireEvent.change(screen.getByLabelText('End date'), { target: { value: endDate } })
    await user.click(screen.getByRole('button', { name: 'Prepare CSV' }))

    await screen.findByRole('link', {
      name: `Download traffic-history_${startDate}_to_${endDate}.csv`,
    })
    expect(fetch).toHaveBeenCalledWith(
      '/api/traffic-history/export',
      expect.objectContaining({
        method: 'POST',
        cache: 'no-store',
        body: expect.stringContaining('"action":"BLOCKED"'),
      })
    )
    const requestBody = JSON.parse(vi.mocked(fetch).mock.calls[0][1]?.body as string)
    expect(requestBody).toMatchObject({
      start_date: startDate,
      end_date: endDate,
      include_normal: true,
      search: 'SQLi',
      confidence_level: ['HIGH', 'MEDIUM'],
      action: 'BLOCKED',
    })
    expect(requestBody).not.toHaveProperty('window')
    expect(requestBody).not.toHaveProperty('page')
    expect(screen.getByRole('status')).toHaveTextContent('CSV export is ready to download.')
  })

  it('shows an obvious header close button and closes the dialog', async () => {
    const user = userEvent.setup()
    render(<TrafficHistoryExportButton role="ANALYST" />)
    await user.click(screen.getByRole('button', { name: 'Export CSV' }))

    const dialog = screen.getByRole('dialog') as HTMLDialogElement
    expect(screen.getByRole('button', { name: 'Close export dialog' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Close export dialog' }))

    expect(dialog.open).toBe(false)
    await user.click(screen.getByRole('button', { name: 'Export CSV' }))
    await user.click(screen.getByRole('button', { name: 'Close' }))
    expect(dialog.open).toBe(false)
  })

  it('keeps the dialog closed until requested and blocks future dates in the form', async () => {
    const user = userEvent.setup()
    render(<TrafficHistoryExportButton role="ANALYST" />)

    const dialog = document.querySelector('dialog') as HTMLDialogElement
    expect(dialog.open).toBe(false)
    expect(dialog).not.toHaveClass('flex')
    expect(dialog).toHaveClass('open:flex')

    await user.click(screen.getByRole('button', { name: 'Export CSV' }))
    const startDate = screen.getByLabelText('Start date') as HTMLInputElement
    const endDate = screen.getByLabelText('End date') as HTMLInputElement
    const today = endDate.value
    expect(dialog.open).toBe(true)
    expect(startDate.max).toBe(today)
    expect(endDate.max).toBe(today)

    fireEvent.change(endDate, { target: { value: addCalendarDays(today, 1) } })
    await user.click(screen.getByRole('button', { name: 'Prepare CSV' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Choose today or an earlier date.'
    )
    expect(startDate).toHaveAttribute('aria-invalid', 'false')
    expect(endDate).toHaveAttribute('aria-invalid', 'true')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('rejects a range over the limit in the dialog and does not call the BFF', async () => {
    const user = userEvent.setup()
    render(<TrafficHistoryExportButton role="OWNER" />)
    await user.click(screen.getByRole('button', { name: 'Export CSV' }))
    const endDate = (screen.getByLabelText('End date') as HTMLInputElement).value
    fireEvent.change(screen.getByLabelText('Start date'), {
      target: { value: addCalendarDays(endDate, -31) },
    })
    await user.click(screen.getByRole('button', { name: 'Prepare CSV' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('31 calendar days or fewer')
    expect(fetch).not.toHaveBeenCalled()
  })

  it('announces upstream failures without exposing an untrusted response body', async () => {
    const user = userEvent.setup()
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response(JSON.stringify({ error: { message: 'Narrow the date range and retry.' } }), {
        status: 413,
        headers: { 'Content-Type': 'application/json' },
      })
    )
    render(<TrafficHistoryExportButton role="ADMIN" />)
    await user.click(screen.getByRole('button', { name: 'Export CSV' }))
    await user.click(screen.getByRole('button', { name: 'Prepare CSV' }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Narrow the date range and retry.'))
  })
})
