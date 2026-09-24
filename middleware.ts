import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import {
  applicationBlockAppliedLogEvent,
  enforcementRuntimeLogEvent,
} from './lib/enforcement-check';
import { checkEnforcementForHeaders } from './lib/enforcement-check-runtime';
import { enforcementPageResponse } from './lib/enforcement-boundary';

export async function middleware(request: NextRequest) {
  const result = await checkEnforcementForHeaders(
    'RECORD_SEARCH',
    request.headers,
  );
  const checkLog = enforcementRuntimeLogEvent(result);
  if (checkLog) console.warn(JSON.stringify(checkLog));

  if (result.decision === 'BLOCK') {
    console.info(
      JSON.stringify(applicationBlockAppliedLogEvent('RECORD_SEARCH')),
    );
  } else if (result.decision === 'THROTTLE') {
    console.info(
      JSON.stringify({
        event: 'enforcement.application_throttle_applied',
        scope: 'RECORD_SEARCH',
        actual_decision: 'THROTTLE',
        retry_after_seconds: result.retryAfterSeconds,
        decision_reason: result.decisionReason,
      }),
    );
  }

  return enforcementPageResponse(result) ?? NextResponse.next();
}

export const config = {
  matcher: ['/records/search'],
  runtime: 'nodejs',
};
