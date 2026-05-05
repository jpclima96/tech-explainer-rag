import type { FactCheckResponse } from '../api/types'
import { ClaimCard } from './ClaimCard'

const PATTERN_LABELS: Record<string, string> = {
  cherry_picking: 'Cherry Picking',
  missing_context: 'Missing Context',
  statistical_manipulation: 'Statistical Manipulation',
  outdated_info: 'Outdated Information',
  false_equivalence: 'False Equivalence',
}

function assessmentClasses(text: string): string {
  if (text.includes('HIGH'))     return 'bg-emerald-50 border-l-4 border-emerald-500 text-emerald-900'
  if (text.includes('MODERATE')) return 'bg-amber-50 border-l-4 border-amber-500 text-amber-900'
  if (text.includes('LOW'))      return 'bg-red-50 border-l-4 border-red-500 text-red-900'
  if (text.includes('MIXED'))    return 'bg-violet-50 border-l-4 border-violet-500 text-violet-900'
  return 'bg-slate-50 border-l-4 border-slate-400 text-slate-800'
}

interface Props {
  data: FactCheckResponse
  onNewCheck: () => void
}

export function ResultsView({ data, onNewCheck }: Props) {
  return (
    <div className="space-y-5">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Results</h2>
        <button
          onClick={onNewCheck}
          className="text-sm text-indigo-600 hover:text-indigo-800 hover:underline focus:outline-none focus:ring-2 focus:ring-indigo-500 rounded"
        >
          ← New check
        </button>
      </div>

      {/* Overall assessment banner */}
      <div className={`rounded-lg px-4 py-3 text-sm font-medium ${assessmentClasses(data.overall_assessment)}`}>
        {data.overall_assessment}
      </div>

      {/* Emotional manipulation warning */}
      {data.emotional_manipulation_detected && (
        <div className="rounded-lg border border-orange-300 bg-orange-50 px-4 py-3 text-sm text-orange-900 flex items-start gap-2">
          <span className="text-orange-500 text-base leading-none mt-0.5">⚠</span>
          <span><strong>Emotionally manipulative language detected</strong> — this text may use fear or outrage to influence the reader.</span>
        </div>
      )}

      {/* Misinformation patterns */}
      {data.misinformation_patterns.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {data.misinformation_patterns.map(p => (
            <span
              key={p}
              className="inline-flex items-center rounded-full bg-rose-100 text-rose-700 text-xs font-medium px-2.5 py-0.5"
            >
              {PATTERN_LABELS[p] ?? p}
            </span>
          ))}
        </div>
      )}

      {/* Claims */}
      {data.claims.length === 0 ? (
        <p className="text-sm text-slate-500 text-center py-8">No verifiable claims were found in the text.</p>
      ) : (
        <div className="space-y-3">
          <p className="text-xs text-slate-500 uppercase tracking-wide font-medium">
            {data.claims.length} claim{data.claims.length !== 1 ? 's' : ''} analyzed
          </p>
          {data.claims.map((claim, i) => (
            <ClaimCard key={i} claim={claim} index={i} />
          ))}
        </div>
      )}
    </div>
  )
}
