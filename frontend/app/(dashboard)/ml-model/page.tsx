import { forbidden, redirect } from 'next/navigation'

import { getSession } from '@/lib/auth-session'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { MLModelWorkspace } from '@/components/ml-model/MLModelWorkspace'

export default async function MLModelPage() {
  const session = await getSession()
  const authorization = await requirePermission(session, PERMISSIONS.ML_MODEL_READ)
  if (!authorization.ok) {
    if (!session || authorization.response.status === 401) redirect('/login')
    forbidden()
  }

  return <MLModelWorkspace role={session?.user?.role} />
}
