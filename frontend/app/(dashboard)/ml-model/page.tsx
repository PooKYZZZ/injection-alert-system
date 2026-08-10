import { getSession } from '@/lib/auth-session'
import { MLModelWorkspace } from '@/components/ml-model/MLModelWorkspace'

export default async function MLModelPage() {
  const session = await getSession()

  return <MLModelWorkspace role={session?.user?.role} />
}
