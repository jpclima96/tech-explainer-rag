import type { Source } from '../api/types'

function credibilityMeta(score: number): { label: string; classes: string } {
  if (score >= 0.90) return { label: 'High',  classes: 'bg-emerald-100 text-emerald-700' }
  if (score >= 0.70) return { label: 'Good',  classes: 'bg-blue-100 text-blue-700' }
  if (score >= 0.45) return { label: 'Fair',  classes: 'bg-amber-100 text-amber-700' }
  return               { label: 'Low',   classes: 'bg-red-100 text-red-700' }
}

export function SourcesList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null

  return (
    <div className="mt-3 space-y-1.5">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Sources</p>
      <ul className="space-y-1">
        {sources.map((s, i) => {
          const { label, classes } = credibilityMeta(s.credibility_score)
          return (
            <li key={i} className="flex items-center gap-2 text-sm">
              <a
                href={s.url}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={`${s.title} (opens in new tab)`}
                className="text-indigo-600 hover:text-indigo-800 hover:underline truncate max-w-xs"
              >
                {s.title || s.url}
              </a>
              <span className={`shrink-0 text-xs px-1.5 py-0.5 rounded font-medium ${classes}`}
                    aria-label={`Source credibility: ${label}`}>
                {label}
              </span>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
