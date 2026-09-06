import { NextRequest, NextResponse } from 'next/server'
import { z } from 'zod'
import { auth } from '@/auth'
import { submitAlertLabelReview } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { VERIFIED_LABEL_VALUES } from '@/features/alerts/contract'

const LabelReviewBodySchema = z
  .object({
    verified_label: z.enum(VERIFIED_LABEL_VALUES),
    approval_state: z.enum(['approved_for_training', 'excluded_from_training']),
    review_note: z.string().max(1000).optional(),
  })
  .strict()

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(
      session,
      PERMISSIONS.TRAINING_FEEDBACK_MANAGE
    )
    if (!authorization.ok) return authorization.response

    const { id } = await params
    if (!/^[1-9]\d*$/.test(id)) {
      return NextResponse.json(
        { error: { code: 'INVALID_ID', message: 'Alert ID must be a valid number.' } },
        { status: 400 }
      )
    }
    if (typeof session?.user?.id !== 'string' || typeof session?.user?.role !== 'string') {
      return NextResponse.json(
        { error: { code: 'FORBIDDEN', message: 'Reviewer context is unavailable.' } },
        { status: 403 }
      )
    }

    let rawBody: unknown
    try {
      rawBody = await request.json()
    } catch {
      return NextResponse.json(
        { error: { code: 'INVALID_REQUEST', message: 'Request body must be valid JSON.' } },
        { status: 400 }
      )
    }
    const parsed = LabelReviewBodySchema.safeParse(rawBody)
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: 'INVALID_REQUEST', message: 'Invalid verified label review.' } },
        { status: 400 }
      )
    }

    const result = await submitAlertLabelReview(id, parsed.data, {
      id: session.user.id,
      role: session.user.role,
    })
    if (!result.ok) {
      const response = NextResponse.json({ error: result.error }, { status: result.status })
      if (result.retryAfter) response.headers.set('Retry-After', result.retryAfter)
      return response
    }
    return NextResponse.json(result.data)
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500 }
    )
  }
}
