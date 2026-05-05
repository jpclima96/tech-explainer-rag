import type { Classification } from '../api/types'

const META: Record<Classification, { label: string; classes: string }> = {
  true:          { label: 'True',          classes: 'bg-emerald-100 text-emerald-800 ring-1 ring-emerald-300' },
  false:         { label: 'False',         classes: 'bg-red-100 text-red-800 ring-1 ring-red-300' },
  misleading:    { label: 'Misleading',    classes: 'bg-amber-100 text-amber-800 ring-1 ring-amber-300' },
  unverifiable:  { label: 'Unverifiable',  classes: 'bg-slate-100 text-slate-600 ring-1 ring-slate-300' },
}

export function ClassificationBadge({ value }: { value: Classification }) {
  const { label, classes } = META[value]
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold ${classes}`}>
      {label}
    </span>
  )
}
