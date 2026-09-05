export function AccessDenied() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background-main px-6">
      <section className="max-w-md rounded-lg border border-border-light bg-surface-panel p-6 text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-text-muted">403</p>
        <h1 className="mt-2 text-xl font-semibold text-text-primary">Access denied</h1>
        <p className="mt-2 text-sm leading-6 text-text-secondary">
          Your account is not authorized to access this section.
        </p>
      </section>
    </main>
  )
}
