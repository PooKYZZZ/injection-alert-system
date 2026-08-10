import { queryOptions, useQuery } from '@tanstack/react-query'
import { RetrainingRunDetailSchema, RetrainingRunListSchema, RetrainingSummarySchema } from './schemas'
import type { RetrainingRunDetail, RetrainingRunList, RetrainingSummary } from './types'

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

export function mlModelSummaryOptions() {
  return queryOptions<RetrainingSummary>({
    queryKey: mlModelKeys.summary(),
    queryFn: () => getJson('/api/ml-model/summary', RetrainingSummarySchema),
    staleTime: 10_000,
  })
}

export function mlModelRunsOptions() {
  return queryOptions<RetrainingRunList>({
    queryKey: mlModelKeys.runs(),
    queryFn: () => getJson('/api/ml-model/runs', RetrainingRunListSchema),
    staleTime: 5_000,
  })
}

export function mlModelRunOptions(runId: string) {
  return queryOptions<RetrainingRunDetail>({
    queryKey: mlModelKeys.run(runId),
    queryFn: () =>
      getJson(`/api/ml-model/runs/${encodeURIComponent(runId)}`, RetrainingRunDetailSchema),
    enabled: runId.length > 0,
    staleTime: 5_000,
  })
}

export const useMLModelSummary = () => useQuery(mlModelSummaryOptions())
export const useMLModelRuns = () => useQuery(mlModelRunsOptions())
export const useMLModelRun = (runId: string) => useQuery(mlModelRunOptions(runId))
