import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@/auth'
import { getStats } from '@/lib/bff-client'

export async function GET(request: NextRequest): Promise<Response> {
  try {
    const session = await auth()
    if (!session) {
      return NextResponse.json(
        { error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' } },
        { status: 401 }
      )
    }

    const timeWindow = request.nextUrl.searchParams.get('window') ?? undefined
    const result = await getStats(timeWindow)
    if (!result.ok) {
      const response = NextResponse.json({ error: result.error }, { status: result.status })
      if (result.retryAfter) {
        response.headers.set('Retry-After', result.retryAfter)
      }
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
