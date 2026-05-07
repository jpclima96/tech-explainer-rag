import type { FactCheckResponse } from '../lib/api'
import { assessmentColor, PATTERN_LABELS } from '../lib/style'
import { ClaimCard } from './ClaimCard'

interface Props {
  data: FactCheckResponse
  onReset: () => void
}

export function Results({ data, onReset }: Props) {
  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Results</h2>
        <button
          onClick={onReset}
          className="text-sm text-indigo-600 hover:text-indigo-800 hover:underline focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
        >
          ← New check
        </button>
      </div>

      <div
        className={`rounded-lg px-4 py-3 text-sm font-medium ${assessmentColor(data.overall_assessment)}`}
      >
        {data.overall_assessment}
      </div>

      {data.emotional_manipulation_detected && (
        <div className="rounded-lg border border-orange-300 bg-orange-50 px-4 py-3 text-sm text-orange-900 flex items-start gap-2">
          <span aria-hidden className="text-orange-500 text-base leading-none mt-0.5">
            ⚠
          </span>
          <span>
            <strong>Emotionally manipulative language detected.</strong> The text
            may use fear or outrage to influence the reader.
          </span>
        </div>
      )}

      {data.misinformation_patterns.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {data.misinformation_patterns.map((p) => (
            <span
              key={p}
              className="inline-flex items-center rounded-full bg-rose-100 text-rose-700 text-xs font-medium px-2.5 py-0.5"
            >
              {PATTERN_LABELS[p] ?? p}
            </span>
          ))}
        </div>
      )}

      {data.claims.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-8">
          No verifiable claims were found in the text.
        </p>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">
            {data.claims.length} claim{data.claims.length !== 1 ? 's' : ''}{' '}
            analyzed
          </p>
          {data.claims.map((c, i) => (
            <ClaimCard key={i} claim={c} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
