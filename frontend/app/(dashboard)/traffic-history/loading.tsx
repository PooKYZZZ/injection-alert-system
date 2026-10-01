export default function TrafficHistoryLoading() {
  return (
    <div
      className="flex flex-col gap-4 animate-pulse"
      role="status"
      aria-label="Loading Traffic History"
      aria-busy="true"
    >
      <div className="h-8 w-32 rounded bg-muted" />
      <div className="h-64 w-full rounded bg-muted" />
      <div className="h-48 w-full rounded bg-muted" />
    </div>
  )
}
