import { NextRequest, NextResponse } from 'next/server'

import { auth } from '@/auth'
import { exportTrafficHistoryCsv } from '@/lib/bff-client'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'

const MAX_REQUEST_BYTES = 16 * 1024

async function readBoundedJson(request: Request): Promise<unknown> {
  const declaredLength = Number(request.headers.get('content-length'))
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BYTES) {
    throw new RangeError('request_too_large')
  }
  if (!request.body) return {}

  const reader = request.body.getReader()
  const chunks: Uint8Array[] = []
  let total = 0
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    total += value.byteLength
    if (total > MAX_REQUEST_BYTES) {
      await reader.cancel()
      throw new RangeError('request_too_large')
    }
    chunks.push(value)
  }
  const bytes = new Uint8Array(total)
  let offset = 0
  for (const chunk of chunks) {
    bytes.set(chunk, offset)
    offset += chunk.byteLength
  }
  const text = new TextDecoder('utf-8', { fatal: true }).decode(bytes)
  return text.trim() ? JSON.parse(text) : {}
}

export async function POST(request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    const authorization = await requirePermission(
      session,
      PERMISSIONS.TRAFFIC_EXPORT
    )
    if (!authorization.ok) return authorization.response

    const originError = requireTrustedOrigin(request)
    if (originError) return originError

    if (
      typeof session?.user?.id !== 'string' ||
      typeof session?.user?.role !== 'string'
    ) {
      return NextResponse.json(
        { error: { code: 'FORBIDDEN', message: 'Requester context is unavailable.' } },
        { status: 403, headers: { 'Cache-Control': 'no-store' } }
      )
    }

    let body: unknown
    try {
      body = await readBoundedJson(request)
    } catch (error) {
      const tooLarge = error instanceof RangeError
      return NextResponse.json(
        {
          error: {
            code: tooLarge ? 'REQUEST_TOO_LARGE' : 'INVALID_REQUEST',
            message: tooLarge
              ? 'Export request is too large.'
              : 'Request body must be valid JSON.',
          },
        },
        { status: tooLarge ? 413 : 400, headers: { 'Cache-Control': 'no-store' } }
      )
    }

    const result = await exportTrafficHistoryCsv(body, {
      id: session.user.id,
      role: session.user.role,
    })
    if (!result.ok) {
      return NextResponse.json(
        { error: result.error },
        { status: result.status, headers: { 'Cache-Control': 'no-store' } }
      )
    }

    const fileContent = new ArrayBuffer(result.data.content.byteLength)
    new Uint8Array(fileContent).set(result.data.content)
    return new Response(fileContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="${result.data.filename}"`,
        'Cache-Control': 'private, no-store',
        'X-Content-Type-Options': 'nosniff',
      },
    })
  } catch {
    return NextResponse.json(
      { error: { code: 'INTERNAL_ERROR', message: 'An unexpected error occurred.' } },
      { status: 500, headers: { 'Cache-Control': 'no-store' } }
    )
  }
}
