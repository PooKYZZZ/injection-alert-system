import fs from 'node:fs'
import path from 'node:path'

import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ROLES, type UserRole } from '@/lib/auth/roles'

vi.mock('server-only', () => ({}))

const authMock = vi.fn()
const getRetrainingSummaryMock = vi.fn()
const startRetrainingRunMock = vi.fn()
const exportRetrainingSamplesMock = vi.fn()
const getRetrainingRunsMock = vi.fn()
const getRetrainingRunMock = vi.fn()
const decideRetrainingRunMock = vi.fn()
const deployRetrainingRunMock = vi.fn()
const rollbackRetrainingRunMock = vi.fn()
const retryRetrainingRunMock = vi.fn()
const getAccountForSessionFreshnessMock = vi.fn()

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const runId = 'retrain-20260811T120000Z-000000000001'

vi.mock('@/auth', () => ({ auth: authMock }))

vi.mock('@/lib/bff-client', () => ({
  getRetrainingSummary: getRetrainingSummaryMock,
  startRetrainingRun: startRetrainingRunMock,
  exportRetrainingSamples: exportRetrainingSamplesMock,
  getRetrainingRuns: getRetrainingRunsMock,
  getRetrainingRun: getRetrainingRunMock,
  decideRetrainingRun: decideRetrainingRunMock,
  deployRetrainingRun: deployRetrainingRunMock,
  rollbackRetrainingRun: rollbackRetrainingRunMock,
  retryRetrainingRun: retryRetrainingRunMock,
}))

vi.mock('@/lib/server/db/auth-accounts', () => ({
  getAccountForSessionFreshness: getAccountForSessionFreshnessMock,
}))

function session(role: UserRole = ROLES.OWNER, authzVersion = 1) {
  return {
    user: { id: accountId, role, authz_version: authzVersion },
    expires: '2099-01-01T00:00:00.000Z',
  }
}

function setCurrentAccount(role: UserRole) {
  getAccountForSessionFreshnessMock.mockResolvedValue({
    id: accountId,
    role,
    authzVersion: 1,
    mfaRequired: false,
    disabledAt: null,
  })
}

const okSummary = {
  ok: true,
  data: {
    active_model_version: 'active-v1',
    latest_run_state: 'queued',
    approved_count: 2,
    unreviewed_count: 3,
    excluded_count: 1,
    latest_dataset_version: null,
    run_in_progress: true,
    last_trigger_time: '2026-08-11T12:00:00Z',
  },
} as const

describe('ML Model retraining BFF routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_APP_ORIGIN = 'http://localhost:3000'
    authMock.mockResolvedValue(session(ROLES.OWNER))
    setCurrentAccount(ROLES.OWNER)
    getRetrainingSummaryMock.mockResolvedValue(okSummary)
  })

  it('keeps every route behind the DB-backed permission guard', () => {
    const routeFiles = [
      'ml-model/summary/route.ts',
      'ml-model/export/route.ts',
      'ml-model/runs/route.ts',
      'ml-model/runs/[runId]/route.ts',
      'ml-model/runs/[runId]/decision/route.ts',
      'ml-model/runs/[runId]/deploy/route.ts',
      'ml-model/runs/[runId]/rollback/route.ts',
      'ml-model/runs/[runId]/retry/route.ts',
    ]

    for (const routeFile of routeFiles) {
      const source = fs.readFileSync(path.resolve(__dirname, routeFile), 'utf8')
      expect(source).toContain("import { requirePermission } from '@/lib/auth/route-guard'")
      expect(source).toMatch(/await\s+requirePermission\s*\(/)
    }
  })

  it.each([ROLES.ADMIN, ROLES.ANALYST, ROLES.VIEWER])(
    'rejects %s from reading summary through the BFF',
    async (role) => {
      authMock.mockResolvedValueOnce(session(role))
      setCurrentAccount(role)
      const { GET } = await import('./ml-model/summary/route')

      const response = await GET()

      expect(response.status).toBe(403)
      expect(getRetrainingSummaryMock).not.toHaveBeenCalled()
    }
  )

  it('allows Owner to read summary through the BFF and forwards actor context', async () => {
    authMock.mockResolvedValueOnce(session(ROLES.OWNER))
    setCurrentAccount(ROLES.OWNER)
    const { GET } = await import('./ml-model/summary/route')

    const response = await GET()

    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toContain('application/json')
    expect(getRetrainingSummaryMock).toHaveBeenCalledWith({ id: accountId, role: ROLES.OWNER })
  })

  it('rejects arbitrary paths and flags at the BFF boundary', async () => {
    const { POST } = await import('./ml-model/runs/route')
    const response = await POST(
      new NextRequest('http://localhost:3000/api/ml-model/runs', {
        method: 'POST',
        headers: { origin: 'http://localhost:3000' },
        body: JSON.stringify({
          trigger: 'manual',
          filesystem_path: 'C:/outside',
          training_flags: ['--epochs', '100'],
        }),
      })
    )

    expect(response.status).toBe(400)
    expect(startRetrainingRunMock).not.toHaveBeenCalled()
  })

  it('forwards the requester browser timezone when starting a run', async () => {
    startRetrainingRunMock.mockResolvedValueOnce({
      ok: true,
      data: {
        run_id: runId,
        state: 'queued',
        stage: 'queued',
        created: true,
        attempt: 0,
      },
    })
    const { POST } = await import('./ml-model/runs/route')

    const response = await POST(
      new NextRequest('http://localhost:3000/api/ml-model/runs', {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3000',
          'X-Requester-Timezone': 'America/New_York',
        },
        body: JSON.stringify({ trigger: 'manual' }),
      })
    )

    expect(response.status).toBe(202)
    expect(startRetrainingRunMock).toHaveBeenCalledWith(
      { trigger: 'manual' },
      { id: accountId, role: ROLES.OWNER },
      'America/New_York'
    )
  })

  it('requires Owner permission for decisions', async () => {
    authMock.mockResolvedValueOnce(session(ROLES.ANALYST))
    setCurrentAccount(ROLES.ANALYST)
    const { POST } = await import('./ml-model/runs/[runId]/decision/route')

    const response = await POST(
      new NextRequest(`http://localhost:3000/api/ml-model/runs/${runId}/decision`, {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3000',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ decision: 'hold', reason: 'need more evidence' }),
      }),
      { params: Promise.resolve({ runId }) }
    )

    expect(response.status).toBe(403)
    expect(decideRetrainingRunMock).not.toHaveBeenCalled()
  })

  it('rejects traversal-shaped run IDs before calling the BFF client', async () => {
    const { GET } = await import('./ml-model/runs/[runId]/route')

    const response = await GET(
      new NextRequest('http://localhost:3000/api/ml-model/runs/%2e%2e%2fsecret'),
      { params: Promise.resolve({ runId: '../secret' }) }
    )

    expect(response.status).toBe(400)
    expect(getRetrainingRunMock).not.toHaveBeenCalled()
  })

  it('rejects model paths at the deployment boundary', async () => {
    const { POST } = await import('./ml-model/runs/[runId]/deploy/route')

    const response = await POST(
      new NextRequest(`http://localhost:3000/api/ml-model/runs/${runId}/deploy`, {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3000',
          'content-type': 'application/json',
        },
        body: JSON.stringify({ expected_candidate_version: 'C:/models/candidate' }),
      }),
      { params: Promise.resolve({ runId }) }
    )

    expect(response.status).toBe(400)
    expect(deployRetrainingRunMock).not.toHaveBeenCalled()
  })

  it('propagates an operator retry without accepting training options', async () => {
    retryRetrainingRunMock.mockResolvedValue({
      ok: true,
      data: { run_id: runId, state: 'queued' },
    })
    const { POST } = await import('./ml-model/runs/[runId]/retry/route')

    const response = await POST(
      new NextRequest(`http://localhost:3000/api/ml-model/runs/${runId}/retry`, {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3000',
          'content-type': 'application/json',
        },
        body: JSON.stringify({}),
      }),
      { params: Promise.resolve({ runId }) }
    )

    expect(response.status).toBe(202)
    expect(retryRetrainingRunMock).toHaveBeenCalledWith(
      runId,
      {},
      {
        id: accountId,
        role: ROLES.OWNER,
      }
    )
  })
})
