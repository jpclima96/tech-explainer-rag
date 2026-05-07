import type { Claim } from '../lib/api'
import {
  CLASSIFICATION_META,
  confidenceColor,
  credibilityTier,
} from '../lib/style'

export function ClaimCard({ claim, index }: { claim: Claim; index: number }) {
  const meta = CLASSIFICATION_META[claim.classification]
  const pct = Math.round(claim.confidence_score * 100)

  return (
    <article
      aria-label={`Claim ${index + 1}`}
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm space-y-3"
    >
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-slate-800 leading-snug">
          {claim.claim}
        </p>
        <span
          className={`shrink-0 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${meta.classes}`}
        >
          {meta.label}
        </span>
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>Confidence</span>
          <span>{pct}%</span>
        </div>
        <div
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={`Confidence: ${pct}%`}
          className="h-2 w-full rounded-full bg-slate-200 overflow-hidden"
        >
          <div
            className={`h-full rounded-full transition-all duration-700 ease-out ${confidenceColor(claim.confidence_score)}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      </div>

      {/* Explanation */}
      <details className="group">
        <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-700 select-none list-none flex items-center gap-1.5">
          <span className="inline-block transition-transform group-open:rotate-90">▶</span>
          Explanation
        </summary>
        <p className="mt-2 text-sm text-slate-600 leading-relaxed">
          {claim.explanation}
        </p>
      </details>

      {/* Sources */}
      {claim.sources.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">
            Sources
          </p>
          <ul className="space-y-1">
            {claim.sources.map((s, i) => {
              const tier = credibilityTier(s.credibility_score)
              return (
                <li key={i} className="flex items-center gap-2 text-sm">
                  <a
                    href={s.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${s.title} (opens in new tab)`}
                    className="text-indigo-600 hover:text-indigo-800 hover:underline truncate max-w-md"
                  >
                    {s.title || s.url}
                  </a>
                  <span
                    aria-label={`Source credibility: ${tier.label}`}
                    className={`shrink-0 text-xs px-1.5 py-0.5 rounded font-medium ${tier.classes}`}
                  >
                    {tier.label}
                  </span>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </article>
  )
}
