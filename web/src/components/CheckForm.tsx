import { useState } from 'react'
import type { FactCheckRequest, Language } from '../lib/api'

interface Props {
  onSubmit: (req: FactCheckRequest) => void
  disabled: boolean
}

export function CheckForm({ onSubmit, disabled }: Props) {
  const [text, setText] = useState('')
  const [context, setContext] = useState('')
  const [language, setLanguage] = useState<Language>('en')

  const len = text.length
  const valid = len >= 10 && len <= 50_000

  const counterColor =
    len > 50_000 ? 'text-red-500' : len > 48_000 ? 'text-amber-500' : 'text-slate-400'

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (!valid || disabled) return
        onSubmit({ text, context: context || undefined, language })
      }}
      className="space-y-4"
    >
      <div>
        <label htmlFor="ft-text" className="block text-sm font-medium text-slate-700 mb-1">
          Text to fact-check
        </label>
        <textarea
          id="ft-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={disabled}
          rows={8}
          placeholder="Paste any article, post, or statement you want to verify…"
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50 disabled:text-slate-400 resize-y"
        />
        <p className={`text-xs text-right mt-1 ${counterColor}`}>
          {len.toLocaleString()} / 50,000
        </p>
      </div>

      <details className="group">
        <summary className="cursor-pointer text-sm text-slate-500 hover:text-slate-700 select-none list-none flex items-center gap-1.5">
          <span className="inline-block transition-transform group-open:rotate-90">▶</span>
          Add context <span className="text-slate-400">(optional)</span>
        </summary>
        <textarea
          aria-label="Additional context"
          value={context}
          onChange={(e) => setContext(e.target.value)}
          disabled={disabled}
          rows={3}
          maxLength={5000}
          placeholder="Background or context that might help with verification…"
          className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50 resize-y"
        />
        <p className="text-xs text-right text-slate-400">{context.length}/5,000</p>
      </details>

      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <label htmlFor="ft-lang" className="text-sm text-slate-600">
            Language
          </label>
          <select
            id="ft-lang"
            value={language}
            onChange={(e) => setLanguage(e.target.value as Language)}
            disabled={disabled}
            className="rounded-md border border-slate-300 text-sm px-2 py-1.5 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-slate-50"
          >
            <option value="en">English</option>
            <option value="pt-BR">Português (BR)</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={!valid || disabled}
          className="px-5 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {disabled ? 'Checking…' : 'Check facts'}
        </button>
      </div>
    </form>
  )
}
