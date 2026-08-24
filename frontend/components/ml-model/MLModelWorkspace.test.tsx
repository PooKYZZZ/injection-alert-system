import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ROLES } from '@/lib/auth/roles'
import type {
  RetrainingRun,
  RetrainingRunDetail,
  RetrainingSummary,
} from '@/features/ml-model/types'
import {
  useDecisionRetrainingMutation,
  useDeployRetrainingMutation,
  useExportRetrainingMutation,
  useMLModelRun,
  useMLModelRuns,
  useMLModelSummary,
  useRollbackRetrainingMutation,
  useRetryRetrainingMutation,
  useStartRetrainingMutation,
} from '@/features/ml-model/queries'
import { MLModelWorkspace } from './MLModelWorkspace'

vi.mock('@/features/ml-model/queries', () => ({
  useDecisionRetrainingMutation: vi.fn(),
  useDeployRetrainingMutation: vi.fn(),
  useExportRetrainingMutation: vi.fn(),
  useMLModelRun: vi.fn(),
  useMLModelRuns: vi.fn(),
  useMLModelSummary: vi.fn(),
  useRollbackRetrainingMutation: vi.fn(),
  useRetryRetrainingMutation: vi.fn(),
  useStartRetrainingMutation: vi.fn(),
}))

const mockedUseSummary = vi.mocked(useMLModelSummary)
const mockedUseRuns = vi.mocked(useMLModelRuns)
const mockedUseRun = vi.mocked(useMLModelRun)
const mockedUseStart = vi.mocked(useStartRetrainingMutation)
const mockedUseExport = vi.mocked(useExportRetrainingMutation)
const mockedUseDecision = vi.mocked(useDecisionRetrainingMutation)
const mockedUseDeploy = vi.mocked(useDeployRetrainingMutation)
const mockedUseRollback = vi.mocked(useRollbackRetrainingMutation)
const mockedUseRetry = vi.mocked(useRetryRetrainingMutation)

const digest = (letter: string) => letter.repeat(64)

const summary: RetrainingSummary = {
  active_model_version: 'active-v1',
  latest_run_state: 'queued',
  approved_count: 12,
  unreviewed_count: 4,
  excluded_count: 2,
  latest_dataset_version: 'dashboard-20260811',
  run_in_progress: false,
  last_trigger_time: '2026-08-11T04:00:00Z',
}

function run(overrides: Partial<RetrainingRun> = {}): RetrainingRun {
  return {
    run_id: 'retrain-20260811T120000Z-000000000001',
    state: 'queued',
    stage: 'queued',
    attempt: 0,
    retry_count: 0,
    max_retries: 2,
    created_at: '2026-08-11T04:00:00Z',
    updated_at: '2026-08-11T04:00:00Z',
    heartbeat_at: null,
    trigger: 'manual',
    requested_by: 'analyst-1',
    requested_timezone: 'Asia/Manila',
    input_fingerprint: digest('a'),
    source_review_revisions: ['1:1'],
    source_dataset_version: 'v3_907k_cleaned',
    source_dataset_digest: digest('b'),
    pipeline_fingerprint: digest('c'),
    active_model_version: 'active-v1',
    active_model_digest: digest('d'),
    approved_sample_count: 12,
    operator_note: null,
    worker_id: null,
    next_retry_at: null,
    dataset_version: null,
    dataset_digest: null,
    candidate_model_version: null,
    candidate_model_digest: null,
    evaluation_digest: null,
    error_code: null,
    error_message: null,
    generation: 1,
    ...overrides,
  }
}

function detail(overrides: Partial<RetrainingRunDetail> = {}): RetrainingRunDetail {
  return {
    ...run(),
    events: [],
    heartbeat_age_seconds: null,
    evidence_status: 'NOT_RUN',
    retry_available: false,
    evidence_summary: {
      preprocessing_version: null,
      evaluation_split: null,
      evaluation_status: 'NOT_RUN',
      comparison_status: 'NOT_RUN',
      metrics: [],
    },
    ...overrides,
  }
}

function mutation() {
  return { mutateAsync: vi.fn().mockResolvedValue(undefined), isPending: false, error: null }
}

function setHarness({
  runs = [run()],
  selectedRun = detail(),
  summaryData = summary,
  isPending = false,
  isError = false,
  detailPending = false,
  detailError = false,
  mutations = {},
}: {
  runs?: RetrainingRun[]
  selectedRun?: RetrainingRunDetail
  summaryData?: RetrainingSummary
  isPending?: boolean
  isError?: boolean
  detailPending?: boolean
  detailError?: boolean
  mutations?: Record<string, ReturnType<typeof mutation>>
} = {}) {
  mockedUseSummary.mockReturnValue({
    data: summaryData,
    isPending,
    isError,
    refetch: vi.fn(),
  } as never)
  mockedUseRuns.mockReturnValue({
    data: { runs },
    isPending,
    isError,
    refetch: vi.fn(),
  } as never)
  mockedUseRun.mockReturnValue({
    data: selectedRun,
    isPending: detailPending,
    isError: detailError,
    refetch: vi.fn(),
  } as never)
  mockedUseStart.mockReturnValue((mutations.start ?? mutation()) as never)
  mockedUseExport.mockReturnValue((mutations.export ?? mutation()) as never)
  mockedUseDecision.mockReturnValue((mutations.decision ?? mutation()) as never)
  mockedUseDeploy.mockReturnValue((mutations.deploy ?? mutation()) as never)
  mockedUseRollback.mockReturnValue((mutations.rollback ?? mutation()) as never)
  mockedUseRetry.mockReturnValue((mutations.retry ?? mutation()) as never)
}

beforeEach(() => {
  vi.clearAllMocks()
  setHarness()
})

afterEach(() => {
  cleanup()
})

describe('MLModelWorkspace', () => {
  it('renders loading, error, and empty-run states honestly', () => {
    setHarness({ isPending: true, summaryData: undefined as never })
    const { rerender } = render(<MLModelWorkspace role={ROLES.VIEWER} />)
    expect(screen.getByText('Loading Model Operations')).toBeInTheDocument()

    setHarness({ isError: true, summaryData: undefined as never })
    rerender(<MLModelWorkspace role={ROLES.VIEWER} />)
    expect(screen.getByText('Failed to load Model Operations')).toBeInTheDocument()

    setHarness({ runs: [] })
    rerender(<MLModelWorkspace role={ROLES.VIEWER} />)
    expect(screen.getByText('No retraining runs have been requested yet.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Request retraining' })).toBeInTheDocument()
  })

  it('shows the overview, queued stage, and unavailable evidence without inventing metrics', () => {
    render(<MLModelWorkspace role={ROLES.ANALYST} />)

    expect(screen.getAllByText('active-v1').length).toBeGreaterThan(0)
    expect(screen.getAllByText('12').length).toBeGreaterThan(0)
    expect(screen.getAllByText('queued').length).toBeGreaterThan(0)
    expect(screen.getByText('Request retraining')).toBeDisabled()
    expect(screen.getByText('Export approved samples')).toBeDisabled()
    expect(screen.getAllByText('True Normal false-positive rate').length).toBeGreaterThan(0)
    expect(screen.getAllByText('NOT_RUN').length).toBeGreaterThan(0)
    expect(screen.getByText(/ground-truth evidence uses verified_label/i)).toBeInTheDocument()
  })

  it('warns the operator when published evidence is invalid', () => {
    setHarness({
      selectedRun: detail({
        state: 'pending_approval',
        evidence_status: 'INVALID',
        evaluation_digest: digest('f'),
        evidence_summary: {
          preprocessing_version: null,
          evaluation_split: null,
          evaluation_status: 'INVALID',
          comparison_status: 'INVALID',
          metrics: [],
        },
      }),
    })

    render(<MLModelWorkspace role={ROLES.ADMIN} />)

    expect(screen.getByText(/published evaluation evidence is missing, unreadable/i)).toBeInTheDocument()
  })

  it('does not invent detail evidence or controls while the selected run detail is unavailable', () => {
    setHarness({
      selectedRun: null as never,
      detailPending: true,
      runs: [
        run({
          state: 'pending_approval',
          candidate_model_version: 'candidate-v1',
          candidate_model_digest: digest('e'),
          evaluation_digest: digest('f'),
        }),
      ],
    })
    render(<MLModelWorkspace role={ROLES.ADMIN} />)

    expect(screen.queryByRole('heading', { name: 'Candidate decision' })).not.toBeInTheDocument()
    expect(screen.getByRole('status', { name: 'Loading selected run evidence' })).toBeInTheDocument()
  })

  it('keeps manual request and export actions on the typed BFF boundary', async () => {
    const start = mutation()
    const exportSamples = mutation()
    setHarness({
      runs: [],
      mutations: { start, export: exportSamples },
    })
    render(<MLModelWorkspace role={ROLES.ADMIN} />)

    fireEvent.click(screen.getByRole('button', { name: 'Request retraining' }))
    fireEvent.click(screen.getByRole('button', { name: 'Export approved samples' }))

    await waitFor(() => {
      expect(start.mutateAsync).toHaveBeenCalledWith({ trigger: 'manual' })
      expect(exportSamples.mutateAsync).toHaveBeenCalledWith()
    })
  })

  it('explains when an idempotent request or export is not a new run', async () => {
    const start = mutation()
    start.mutateAsync.mockResolvedValue({
      run_id: 'retrain-existing',
      state: 'NOT_ENOUGH_EVIDENCE',
      stage: 'evidence_comparison',
      created: false,
      attempt: 1,
    })
    const exportSamples = mutation()
    exportSamples.mutateAsync.mockResolvedValue({
      export_id: 'export-existing',
      status: 'QUARANTINED_FOR_REVIEW',
      approved_count: 3,
      exported_count: 1,
      rejected_count: 2,
      excluded_count: 0,
      quarantined: true,
    })
    setHarness({
      runs: [],
      mutations: { start, export: exportSamples },
    })
    render(<MLModelWorkspace role={ROLES.ADMIN} />)

    fireEvent.click(screen.getByRole('button', { name: 'Request retraining' }))
    await waitFor(() => {
      expect(screen.getByText(/No duplicate run was created/i)).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Export approved samples' }))
    await waitFor(() => {
      expect(screen.getByText(/quarantined for review/i)).toBeInTheDocument()
      expect(screen.getByText(/No training run was started/i)).toBeInTheDocument()
    })
  })

  it('shows administrator decision controls only for pending approval and records hold', async () => {
    const decision = mutation()
    setHarness({
      selectedRun: detail({
        state: 'pending_approval',
        stage: 'evidence_comparison',
        candidate_model_version: 'candidate-v1',
        candidate_model_digest: digest('e'),
        evaluation_digest: digest('f'),
        evidence_status: 'NATIVE',
        evidence_summary: {
          preprocessing_version: 'http-preprocessor-v1',
          evaluation_split: 'frozen_test',
          evaluation_status: 'PASS',
          comparison_status: 'PASS',
          metrics: [],
        },
      }),
      mutations: { decision },
    })
    render(<MLModelWorkspace role={ROLES.ADMIN} />)

    expect(screen.getByRole('heading', { name: 'Candidate decision' })).toBeInTheDocument()
    const reason = screen.getByRole('textbox', { name: 'Decision reason' })
    fireEvent.change(reason, { target: { value: 'Keep for a second review.' } })
    fireEvent.click(screen.getByRole('button', { name: 'Hold for next cycle' }))

    await waitFor(() => {
      expect(decision.mutateAsync).toHaveBeenCalledWith({
        runId: 'retrain-20260811T120000Z-000000000001',
        decision: 'hold',
        reason: 'Keep for a second review.',
      })
    })
  })

  it('requires confirmation for approval and shows sample-retention semantics after hold/reject', async () => {
    const decision = mutation()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    setHarness({
      selectedRun: detail({ state: 'held', stage: 'decision_hold' }),
      mutations: { decision },
    })
    const { rerender } = render(<MLModelWorkspace role={ROLES.ADMIN} />)
    expect(screen.getByText(/Verified samples were retained for the next retraining cycle/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Candidate decision' })).not.toBeInTheDocument()

    setHarness({
      selectedRun: detail({
        state: 'pending_approval',
        candidate_model_version: 'candidate-v1',
        candidate_model_digest: digest('e'),
        evaluation_digest: digest('f'),
        evidence_status: 'NATIVE',
        evidence_summary: {
          preprocessing_version: 'http-preprocessor-v1',
          evaluation_split: 'frozen_test',
          evaluation_status: 'PASS',
          comparison_status: 'PASS',
          metrics: [],
        },
      }),
      mutations: { decision },
    })
    rerender(<MLModelWorkspace role={ROLES.ADMIN} />)
    fireEvent.change(screen.getByRole('textbox', { name: 'Decision reason' }), {
      target: { value: 'Approved after review.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Approve candidate' }))

    await waitFor(() => {
      expect(confirm).toHaveBeenCalled()
      expect(decision.mutateAsync).toHaveBeenCalledWith({
        runId: 'retrain-20260811T120000Z-000000000001',
        decision: 'approve',
        reason: 'Approved after review.',
      })
    })
    confirm.mockRestore()
  })

  it('does not offer approval when native comparison evidence fails a gate', () => {
    setHarness({
      selectedRun: detail({
        state: 'pending_approval',
        candidate_model_version: 'candidate-v1',
        candidate_model_digest: digest('e'),
        evaluation_digest: digest('f'),
        evidence_status: 'NATIVE',
        evidence_summary: {
          preprocessing_version: 'http-preprocessor-v1',
          evaluation_split: 'frozen_test',
          evaluation_status: 'PASS',
          comparison_status: 'FAIL',
          metrics: [],
        },
      }),
    })
    render(<MLModelWorkspace role={ROLES.ADMIN} />)

    expect(screen.getByRole('button', { name: 'Approve candidate' })).toBeDisabled()
  })

  it('keeps viewer read-only and exposes safe quarantine/failure next actions', () => {
    setHarness({
      selectedRun: detail({
        state: 'QUARANTINED_FOR_REVIEW',
        stage: 'export',
        error_code: 'SOURCE_CONCENTRATION_LIMIT',
        error_message: 'raw subprocess output must not render',
      }),
    })
    const { rerender } = render(<MLModelWorkspace role={ROLES.VIEWER} />)
    expect(screen.getByText('Quarantined for review')).toBeInTheDocument()
    expect(screen.getByText(/Review approved labels and export limits/i)).toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Candidate decision' })).not.toBeInTheDocument()
    expect(screen.queryByText('raw subprocess output must not render')).not.toBeInTheDocument()

    setHarness({
      selectedRun: detail({ state: 'failed', stage: 'failed', error_code: 'WORKER_EXCEPTION' }),
    })
    rerender(<MLModelWorkspace role={ROLES.VIEWER} />)
    expect(screen.getByText('Worker failed')).toBeInTheDocument()
    expect(screen.getByText(/Keep the active model and inspect the manifest/i)).toBeInTheDocument()
  })

  it('shows an explicit reconciliation action for recoverable staging state', () => {
    setHarness({
      selectedRun: detail({ state: 'RECOVERY_REQUIRED', stage: 'deploy_recovery_required' }),
    })

    render(<MLModelWorkspace role={ROLES.ADMIN} />)

    expect(screen.getByText('Deployment state needs reconciliation')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reconcile with rollback' })).toBeInTheDocument()
  })

  it('shows deploy and rollback only at their explicit local-staging boundaries', () => {
    const deploy = mutation()
    const rollback = mutation()
    const confirm = vi.spyOn(window, 'confirm').mockReturnValue(true)
    setHarness({
      selectedRun: detail({ state: 'approved', candidate_model_version: 'candidate-v1' }),
      mutations: { deploy, rollback },
    })
    const { rerender } = render(<MLModelWorkspace role={ROLES.ADMIN} />)
    expect(screen.getByRole('button', { name: 'Deploy to local staging' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Deploy to local staging' }))
    expect(deploy.mutateAsync).toHaveBeenCalled()

    setHarness({ selectedRun: detail({ state: 'deployed' }), mutations: { deploy, rollback } })
    rerender(<MLModelWorkspace role={ROLES.ADMIN} />)
    expect(screen.getByRole('button', { name: 'Roll back local staging' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Roll back local staging' }))
    expect(rollback.mutateAsync).toHaveBeenCalled()
    expect(confirm).toHaveBeenCalled()
    confirm.mockRestore()
  })
})
