export default function DashboardLoading() {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-sm border border-border-light bg-surface-light p-4 shadow-subtle">
        <div className="h-4 w-44 animate-pulse rounded-sm bg-border-light" />
        <div className="mt-2 h-3 w-72 animate-pulse rounded-sm bg-border-light" />
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <div
            key={index}
            className="rounded-sm border border-border-light bg-surface-light p-4 shadow-subtle"
          >
            <div className="flex items-start justify-between">
              <div className="h-3 w-24 animate-pulse rounded-sm bg-border-light" />
              <div className="h-5 w-5 animate-pulse rounded-sm bg-border-light" />
            </div>
            <div className="mt-3 h-9 w-20 animate-pulse rounded-sm bg-border-light" />
            <div className="mt-3 h-3 w-32 animate-pulse rounded-sm bg-border-light" />
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-4">
        <div className="h-3 w-52 animate-pulse rounded-sm bg-border-light" />
        <div className="grid gap-4 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="rounded-sm border border-border-light bg-surface-light p-4 shadow-subtle"
            >
              <div className="h-4 w-36 animate-pulse rounded-sm bg-border-light" />
              <div className="mt-2 h-3 w-56 animate-pulse rounded-sm bg-border-light" />
              <div className="mt-6 space-y-3">
                {Array.from({ length: 4 }).map((_, rowIndex) => (
                  <div
                    key={rowIndex}
                    className="grid grid-cols-[minmax(0,160px)_1fr_auto] items-center gap-3"
                  >
                    <div className="h-3 w-24 animate-pulse rounded-sm bg-border-light" />
                    <div className="h-3 animate-pulse rounded-full bg-border-light" />
                    <div className="h-3 w-8 animate-pulse rounded-sm bg-border-light" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-sm border border-border-light bg-surface-light shadow-subtle overflow-hidden">
        <div className="border-b border-border-light p-4">
          <div className="h-4 w-24 animate-pulse rounded-sm bg-border-light" />
          <div className="mt-2 h-3 w-72 animate-pulse rounded-sm bg-border-light" />
        </div>
        <div className="p-4 space-y-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="grid grid-cols-[24px_2fr_1fr_1fr_1fr] gap-3">
              <div className="h-4 w-4 animate-pulse rounded-sm bg-border-light" />
              <div className="h-8 animate-pulse rounded-sm bg-border-light" />
              <div className="h-4 animate-pulse rounded-sm bg-border-light" />
              <div className="h-4 animate-pulse rounded-sm bg-border-light" />
              <div className="h-4 animate-pulse rounded-sm bg-border-light" />
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-sm border border-border-light bg-surface-light p-4 shadow-subtle">
        <div className="h-4 w-48 animate-pulse rounded-sm bg-border-light" />
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="h-24 animate-pulse rounded-sm bg-border-light" />
          <div className="h-24 animate-pulse rounded-sm bg-border-light" />
        </div>
      </div>
    </div>
  )
}
