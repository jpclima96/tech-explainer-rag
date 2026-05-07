import { useMutation } from '@tanstack/react-query'
import { ApiError, checkFacts } from './lib/api'
import { CheckForm } from './components/CheckForm'
import { Loading } from './components/Loading'
import { Results } from './components/Results'
import { ErrorBox } from './components/ErrorBox'

export default function App() {
  const mutation = useMutation({
    mutationFn: checkFacts,
    retry: (count, err) => {
      const status = err instanceof ApiError ? err.status : undefined
      if (status === 422 || status === 502 || status === 504) return false
      return count < 1
    },
  })

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 py-10">
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">
            Fact Checker
          </h1>
          <p className="mt-2 text-slate-500 text-sm">
            Paste any text. We extract its factual claims and verify them
            against trusted sources using Claude Opus and live web search.
          </p>
        </header>

        {!mutation.isPending && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
            <CheckForm
              onSubmit={(req) => mutation.mutate(req)}
              disabled={mutation.isPending}
            />
          </div>
        )}

        {mutation.isPending && <Loading />}

        {mutation.isError && (
          <ErrorBox error={mutation.error as Error} onRetry={() => mutation.reset()} />
        )}

        {mutation.isSuccess && mutation.data && (
          <Results data={mutation.data} onReset={() => mutation.reset()} />
        )}

        <footer className="mt-12 text-center text-xs text-slate-400">
          Powered by Claude Opus 4.7 + Tavily search
        </footer>
      </div>
    </div>
  )
}
