import { NextResponse } from 'next/server'

import { RetrainingRunIdSchema } from '@/features/ml-model/schemas'

export function invalidRetrainingRunIdResponse(runId: string): NextResponse | null {
  if (RetrainingRunIdSchema.safeParse(runId).success) return null

  return NextResponse.json(
    { error: { code: 'INVALID_RUN_ID', message: 'Retraining run ID is invalid.' } },
    { status: 400 }
  )
}
