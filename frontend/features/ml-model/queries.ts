import {
  queryOptions,
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'
import {
  RetrainingDecisionRequestSchema,
  RetrainingDecisionResultSchema,
  RetrainingDeployRequestSchema,
  RetrainingExportRequestSchema,
  RetrainingExportResultSchema,
  RetrainingRetryRequestSchema,
  RetrainingRollbackRequestSchema,
  RetrainingRunDetailSchema,
  RetrainingRunListSchema,
  RetrainingRunRequestSchema,
  RetrainingRunStartSchema,
  RetrainingRunSchema,
  RetrainingSummarySchema,
} from './schemas'
import type {
  RetrainingRunDetail,
  RetrainingRunList,
  RetrainingSummary,
} from './types'
import { isRetrainingRunActive } from './contract'
import type { RetrainingDecision } from './contract'

export const mlModelKeys = {
  all: ['ml-model'] as const,
  summary: () => ['ml-model', 'summary'] as const,
  runs: () => ['ml-model', 'runs'] as const,
  run: (runId: string) => ['ml-model', 'runs', runId] as const,
}

async function getJson<T>(path: string, schema: { parse: (value: unknown) => T }): Promise<T> {
  const response = await fetch(path, { cache: 'no-store' })
  if (!response.ok) throw new Error(`${path} responded with ${response.status}`)
  return schema.parse(await response.json())
}

function safeMutationMessage(payload: unknown): string {
  if (!payload || typeof payload !== 'object') return 'Retraining operation failed.'

  const error = (payload as { error?: unknown }).error
  if (!error || typeof error !== 'object') return 'Retraining operation failed.'

  const message = (error as { message?: unknown }).message
  return typeof message === 'string' && message.length > 0
    ? message.slice(0, 240)
    : 'Retraining operation failed.'
}

export class RetrainingMutationError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'RetrainingMutationError'
  }
}

async function postJson<T>(
  path: string,
  body: unknown,
  schema: { parse: (value: unknown) => T },
): Promise<T> {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  let payload: unknown = null
  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  if (!response.ok) {
    throw new RetrainingMutationError(safeMutationMessage(payload), response.status)
  }

  return schema.parse(payload)
}

function hasActiveRun(data: RetrainingRunList | undefined): boolean {
  return data?.runs.some((run) => isRetrainingRunActive(run.state)) ?? false
}

export function mlModelSummaryOptions() {
  return queryOptions<RetrainingSummary>({
    queryKey: mlModelKeys.summary(),
    queryFn: () => getJson('/api/ml-model/summary', RetrainingSummarySchema),
    staleTime: 10_000,
    refetchInterval: (query) => (query.state.data?.run_in_progress ? 3_000 : false),
  })
}

export function mlModelRunsOptions() {
  return queryOptions<RetrainingRunList>({
    queryKey: mlModelKeys.runs(),
    queryFn: () => getJson('/api/ml-model/runs', RetrainingRunListSchema),
    staleTime: 5_000,
    refetchInterval: (query) => (hasActiveRun(query.state.data) ? 3_000 : false),
  })
}

export function mlModelRunOptions(runId: string) {
  return queryOptions<RetrainingRunDetail>({
    queryKey: mlModelKeys.run(runId),
    queryFn: () =>
      getJson(`/api/ml-model/runs/${encodeURIComponent(runId)}`, RetrainingRunDetailSchema),
    enabled: runId.length > 0,
    staleTime: 5_000,
    refetchInterval: (query) =>
      query.state.data && isRetrainingRunActive(query.state.data.state) ? 3_000 : false,
  })
}

export const useMLModelSummary = () => useQuery(mlModelSummaryOptions())
export const useMLModelRuns = () => useQuery(mlModelRunsOptions())
export const useMLModelRun = (runId: string) => useQuery(mlModelRunOptions(runId))

function useRetrainingInvalidation() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: mlModelKeys.all })
}

export function useStartRetrainingMutation() {
  const invalidate = useRetrainingInvalidation()
  return useMutation({
    mutationFn: (input: unknown) =>
      postJson(
        '/api/ml-model/runs',
        RetrainingRunRequestSchema.parse(input),
        RetrainingRunStartSchema,
      ),
    onSuccess: invalidate,
  })
}

export function useExportRetrainingMutation() {
  const invalidate = useRetrainingInvalidation()
  return useMutation({
    mutationFn: () =>
      postJson(
        '/api/ml-model/export',
        RetrainingExportRequestSchema.parse({}),
        RetrainingExportResultSchema,
      ),
    onSuccess: invalidate,
  })
}

export function useRetryRetrainingMutation() {
  const invalidate = useRetrainingInvalidation()
  return useMutation({
    mutationFn: (runId: string) =>
      postJson(
        `/api/ml-model/runs/${encodeURIComponent(runId)}/retry`,
        RetrainingRetryRequestSchema.parse({}),
        RetrainingRunSchema,
      ),
    onSuccess: invalidate,
  })
}

export function useDecisionRetrainingMutation() {
  const invalidate = useRetrainingInvalidation()
  return useMutation({
    mutationFn: ({
      runId,
      decision,
      reason,
    }: {
      runId: string
      decision: RetrainingDecision
      reason: string | null
    }) =>
      postJson(
        `/api/ml-model/runs/${encodeURIComponent(runId)}/decision`,
        RetrainingDecisionRequestSchema.parse({ decision, reason }),
        RetrainingDecisionResultSchema,
      ),
    onSuccess: invalidate,
  })
}

export function useDeployRetrainingMutation() {
  const invalidate = useRetrainingInvalidation()
  return useMutation({
    mutationFn: ({ runId, expectedCandidateVersion }: { runId: string; expectedCandidateVersion: string }) =>
      postJson(
        `/api/ml-model/runs/${encodeURIComponent(runId)}/deploy`,
        RetrainingDeployRequestSchema.parse({
          expected_candidate_version: expectedCandidateVersion,
        }),
        RetrainingRunSchema,
      ),
    onSuccess: invalidate,
  })
}

export function useRollbackRetrainingMutation() {
  const invalidate = useRetrainingInvalidation()
  return useMutation({
    mutationFn: ({
      runId,
      previousStagingVersion,
      reason,
    }: {
      runId: string
      previousStagingVersion: string
      reason: string
    }) =>
      postJson(
        `/api/ml-model/runs/${encodeURIComponent(runId)}/rollback`,
        RetrainingRollbackRequestSchema.parse({
          previous_staging_version: previousStagingVersion,
          reason,
        }),
        RetrainingRunSchema,
      ),
    onSuccess: invalidate,
  })
}
