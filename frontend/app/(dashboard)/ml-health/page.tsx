import { forbidden, redirect } from 'next/navigation'

import { MLHealthWorkspace } from '@/components/ml-health/MLHealthWorkspace'
import { getSession } from '@/lib/auth-session'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'

export default async function MLHealthPage() {
  const session = await getSession()
  const authorization = await requirePermission(session, PERMISSIONS.ML_HEALTH_READ)
  if (!authorization.ok) {
    if (!session || authorization.response.status === 401) redirect('/login')
    forbidden()
  }

  return <MLHealthWorkspace />
}
