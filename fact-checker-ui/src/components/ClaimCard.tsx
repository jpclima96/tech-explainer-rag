import type { Claim } from '../api/types'
import { ClassificationBadge } from './ClassificationBadge'
import { ConfidenceBar } from './ConfidenceBar'
import { SourcesList } from './SourcesList'

export function ClaimCard({ claim, index }: { claim: Claim; index: number }) {
  return (
    <article
      aria-label={`Claim ${index + 1}`}
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-800 leading-snug">{claim.claim}</p>
        <ClassificationBadge value={claim.classification} />
      </div>

      <ConfidenceBar score={claim.confidence_score} />

      <details className="group">
        <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-700 select-none list-none flex items-center gap-1">
          <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
          Explanation
        </summary>
        <p className="mt-2 text-sm text-slate-600 leading-relaxed">{claim.explanation}</p>
      </details>

      <SourcesList sources={claim.sources} />
    </article>
  )
}
