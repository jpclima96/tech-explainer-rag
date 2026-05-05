export function ConfidenceBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const fill =
    score >= 0.75 ? 'bg-emerald-500' :
    score >= 0.50 ? 'bg-amber-400' :
    score >= 0.25 ? 'bg-orange-400' :
                    'bg-red-500'

  return (
    <div className="mt-2">
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>Confidence</span>
        <span>{pct}%</span>
      </div>
      <div
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Confidence score: ${pct}%`}
        className="h-2 w-full rounded-full bg-slate-200 overflow-hidden"
      >
        <div
          className={`h-full rounded-full transition-all duration-700 ease-out ${fill}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
