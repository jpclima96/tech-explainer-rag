// Visual mappings: classifications, confidence, credibility tiers.

import type { Classification } from './api'

export const CLASSIFICATION_META: Record<
  Classification,
  { label: string; classes: string }
> = {
  true: {
    label: 'True',
    classes: 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300',
  },
  false: {
    label: 'False',
    classes: 'bg-red-100 text-red-800 ring-1 ring-red-300',
  },
  misleading: {
    label: 'Misleading',
    classes: 'bg-amber-100 text-amber-800 ring-1 ring-amber-300',
  },
  unverifiable: {
    label: 'Unverifiable',
    classes: 'bg-slate-100 text-slate-600 ring-1 ring-slate-300',
  },
}

export const PATTERN_LABELS: Record<string, string> = {
  cherry_picking: 'Cherry-picking',
  missing_context: 'Missing context',
  statistical_manipulation: 'Statistical manipulation',
  outdated_info: 'Outdated info',
  false_equivalence: 'False equivalence',
}

export function confidenceColor(score: number): string {
  if (score >= 0.75) return 'bg-emerald-500'
  if (score >= 0.5) return 'bg-amber-400'
  if (score >= 0.25) return 'bg-orange-400'
  return 'bg-red-500'
}

export function credibilityTier(score: number): { label: string; classes: string } {
  if (score >= 0.9) return { label: 'High', classes: 'bg-emerald-100 text-emerald-700' }
  if (score >= 0.7) return { label: 'Good', classes: 'bg-blue-100 text-blue-700' }
  if (score >= 0.45) return { label: 'Fair', classes: 'bg-amber-100 text-amber-700' }
  return { label: 'Low', classes: 'bg-red-100 text-red-700' }
}

export function assessmentColor(text: string): string {
  if (text.includes('HIGH'))
    return 'bg-emerald-50 border-l-4 border-emerald-500 text-emerald-900'
  if (text.includes('MODERATE') || text.includes('MODERADA'))
    return 'bg-amber-50 border-l-4 border-amber-500 text-amber-900'
  if (text.includes('LOW') || text.includes('BAIXA'))
    return 'bg-red-50 border-l-4 border-red-500 text-red-900'
  if (text.includes('MIXED') || text.includes('MISTA'))
    return 'bg-violet-50 border-l-4 border-violet-500 text-violet-900'
  return 'bg-slate-50 border-l-4 border-slate-400 text-slate-800'
}
