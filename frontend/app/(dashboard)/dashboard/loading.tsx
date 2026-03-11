export default function DashboardLoading() {
  return (
    <div className="flex flex-col gap-4 animate-pulse">
      <div className="h-12 bg-gray-200 rounded-sm" />
      <div className="grid grid-cols-4 gap-4">
        <div className="h-24 bg-gray-200 rounded-sm" />
        <div className="h-24 bg-gray-200 rounded-sm" />
        <div className="h-24 bg-gray-200 rounded-sm" />
        <div className="h-24 bg-gray-200 rounded-sm" />
      </div>
      <div className="h-20 bg-gray-200 rounded-sm" />
      <div className="h-10 bg-gray-200 rounded-sm" />
      <div className="h-64 bg-gray-200 rounded-sm" />
      <div className="grid grid-cols-2 gap-4">
        <div className="h-48 bg-gray-200 rounded-sm" />
        <div className="h-48 bg-gray-200 rounded-sm" />
      </div>
    </div>
  )
}
