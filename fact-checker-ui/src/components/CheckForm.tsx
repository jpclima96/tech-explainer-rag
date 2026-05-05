import { useState } from 'react'
import type { FactCheckRequest, Language } from '../api/types'

interface Props {
  onSubmit: (req: FactCheckRequest) => void
  isLoading: boolean
}

export function CheckForm({ onSubmit, isLoading }: Props) {
  const [text, setText] = useState('')
  const [context, setContext] = useState('')
  const [language, setLanguage] = useState<Language>('en')

  const charCount = text.length
  const valid = charCount >= 10 && charCount <= 50000

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!valid || isLoading) return
    onSubmit({ text, context: context || undefined, language })
  }

  const counterColor =
    charCount > 50000 ? 'text-red-500' :
    charCount > 48000 ? 'text-amber-500' :
    'text-slate-400'

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="text-input" className="block text-sm font-medium text-slate-700 mb-1">
          Text to fact-check
        </label>
        <textarea
          id="text-input"
          value={text}
          onChange={e => setText(e.target.value)}
          disabled={isLoading}
          placeholder="Paste or type the text you want to verify…"
          rows={7}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 resize-y"
        />
        <p className={`text-xs text-right mt-1 ${counterColor}`}>
          {charCount.toLocaleString()} / 50,000
        </p>
      </div>

      <details className="group">
        <summary className="cursor-pointer text-sm text-slate-500 hover:text-slate-700 select-none list-none flex items-center gap-1">
          <span className="group-open:rotate-90 transition-transform inline-block">▶</span>
          Add context <span className="text-slate-400">(optional)</span>
        </summary>
        <div className="mt-2">
          <textarea
            aria-label="Additional context"
            value={context}
            onChange={e => setContext(e.target.value)}
            disabled={isLoading}
            placeholder="Any additional context that might help verify the claims…"
            rows={3}
            maxLength={5000}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50 resize-y"
          />
          <p className="text-xs text-right text-slate-400">{context.length}/5,000</p>
        </div>
      </details>

      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="language-select" className="text-sm text-slate-600">Language:</label>
          <select
            id="language-select"
            value={language}
            onChange={e => setLanguage(e.target.value as Language)}
            disabled={isLoading}
            className="rounded-md border border-slate-300 text-sm px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50"
          >
            <option value="en">English</option>
            <option value="pt-BR">Português (BR)</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={!valid || isLoading}
          className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? 'Checking…' : 'Check Facts'}
        </button>
      </div>
    </form>
  )
}
