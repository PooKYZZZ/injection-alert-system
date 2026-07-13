import { ResetPasswordForm } from '@/features/user-management/ResetPasswordForm'

export default async function ResetPasswordPage({ searchParams }: { searchParams: Promise<{ token?: string }> }) {
  const params = await searchParams
  return <ResetPasswordForm token={params.token ?? ''} />
}
