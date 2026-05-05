import { useFactCheck } from './hooks/useFactCheck'
import { CheckForm } from './components/CheckForm'
import { LoadingSkeleton } from './components/LoadingSkeleton'
import { ResultsView } from './components/ResultsView'
import { ErrorMessage } from './components/ErrorMessage'
import type { FactCheckRequest } from './api/types'

export default function App() {
  const mutation = useFactCheck()

  function handleSubmit(req: FactCheckRequest) {
    mutation.mutate(req)
  }

  function handleReset() {
    mutation.reset()
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Header */}
        <header className="mb-8 text-center">
          <h1 className="text-3xl font-bold text-slate-900 tracking-tight">Fact Checker</h1>
          <p className="mt-2 text-slate-500 text-sm">
            Paste any text and we'll extract and verify its factual claims using AI and trusted sources.
          </p>
        </header>

        {/* Form — always visible unless loading */}
        {!mutation.isPending && (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 mb-6">
            <CheckForm
              onSubmit={handleSubmit}
              isLoading={mutation.isPending}
            />
          </div>
        )}

        {/* Loading */}
        {mutation.isPending && <LoadingSkeleton />}

        {/* Error */}
        {mutation.isError && (
          <ErrorMessage
            error={mutation.error as Error & { status?: number }}
            onRetry={handleReset}
          />
        )}

        {/* Results */}
        {mutation.isSuccess && mutation.data && (
          <ResultsView data={mutation.data} onNewCheck={handleReset} />
        )}
      </div>
    </div>
  )
}
