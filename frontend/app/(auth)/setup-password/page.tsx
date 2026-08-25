import { SetupPasswordForm } from '@/features/user-management/SetupPasswordForm'

export const dynamic = 'force-dynamic'

export default async function SetupPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>
}) {
  const { token = '' } = await searchParams
  return (
    <section className="w-full max-w-[430px]" aria-labelledby="setup-password-heading">
      <h1 id="setup-password-heading" className="text-[2rem] font-semibold tracking-[-0.04em] text-text-primary">Choose your password</h1>
      <p className="mt-2 text-sm leading-6 text-text-secondary">This single-use link expires after 30 minutes. Opening this page does not consume it.</p>
      <SetupPasswordForm token={token} />
      <a href="/login" className="mt-5 inline-flex text-sm text-text-secondary underline decoration-border-light underline-offset-4 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/60">Return to sign in</a>
    </section>
  )
}
