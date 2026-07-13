import Image from 'next/image'

import { SetupPasswordForm } from '@/features/user-management/SetupPasswordForm'

export const dynamic = 'force-dynamic'

export default async function SetupPasswordPage({
  searchParams,
}: {
  searchParams: Promise<{ token?: string }>
}) {
  const { token = '' } = await searchParams
  return (
    <main className="flex min-h-screen items-center justify-center bg-surface-page px-6 py-12">
      <section className="w-full max-w-md border-y border-border-light py-10">
        <Image src="/logo.png" alt="CyberTrace" width={44} height={44} priority />
        <p className="mt-6 text-[11px] font-semibold uppercase tracking-[0.18em] text-accent-action">Account setup</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text-primary">Choose your password</h1>
        <p className="mt-3 text-sm leading-6 text-text-secondary">This link is single-use and expires after 30 minutes. Opening this page does not consume it.</p>
        <SetupPasswordForm token={token} />
      </section>
    </main>
  )
}
