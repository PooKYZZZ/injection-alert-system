import { VerifyEmailForm } from '@/features/user-management/VerifyEmailForm'
import { authHeadingClass } from '@/components/auth/authStyles'

export const dynamic = 'force-dynamic'

export default async function VerifyEmailPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>
}) {
  const { token = '' } = await searchParams
  return (
    <section className="w-full max-w-[400px]" aria-labelledby="verify-email-heading">
      <h1 id="verify-email-heading" className={authHeadingClass}>Verify your new email</h1>
      <p className="mt-2 text-sm leading-6 text-text-secondary">Confirm access to activate the managed address. Opening this page alone changes nothing.</p>
      <VerifyEmailForm token={token} />
      <a href="/login" className="mt-5 inline-flex text-sm text-text-secondary underline decoration-border-light underline-offset-4 hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/60">Return to sign in</a>
    </section>
  )
}
