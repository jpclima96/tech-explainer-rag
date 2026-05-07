export function Loading() {
  return (
    <div className="space-y-4">
      <p
        role="status"
        aria-live="polite"
        className="text-sm text-slate-500 text-center py-2"
      >
        Analyzing claims — this can take up to 30 seconds…
      </p>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          className="animate-pulse rounded-xl border border-slate-200 bg-white p-5 space-y-3"
        >
          <div className="h-4 bg-slate-200 rounded w-3/4" />
          <div className="h-3 bg-slate-200 rounded w-1/4" />
          <div className="h-2 bg-slate-200 rounded-full w-full" />
          <div className="h-10 bg-slate-200 rounded w-full" />
        </div>
      ))}
    </div>
  )
}
