import { ApiError } from '../lib/api'

const HTTP_MESSAGES: Record<number, { title: string; body: string }> = {
  504: {
    title: 'Search timed out',
    body: 'The service took too long to retrieve sources. Try again or shorten your text.',
  },
  502: {
    title: 'Upstream service error',
    body: 'The fact-checking pipeline could not complete. This is usually temporary — try again in a moment.',
  },
  422: {
    title: 'Invalid input',
    body: 'Your text did not meet the requirements (10–50,000 characters).',
  },
}

interface Props {
  error: Error
  onRetry: () => void
}

export function ErrorBox({ error, onRetry }: Props) {
  const status = error instanceof ApiError ? error.status : undefined
  const info = status ? HTTP_MESSAGES[status] : undefined
  const title = info?.title ?? 'Something went wrong'
  const body = info?.body ?? 'An unexpected error occurred. Please try again.'

  return (
    <div
      role="alert"
      className="rounded-xl border border-red-200 bg-red-50 p-5 space-y-3"
    >
      <div className="flex items-start gap-3">
        <span aria-hidden className="text-red-500 text-xl leading-none mt-0.5">
          ⚠
        </span>
        <div>
          <p className="font-medium text-red-800">{title}</p>
          <p className="text-sm text-red-700 mt-1">{body}</p>
        </div>
      </div>
      <button
        onClick={onRetry}
        className="text-sm font-medium text-red-700 hover:text-red-900 underline focus:outline-none focus:ring-2 focus:ring-red-500 rounded"
      >
        Try again
      </button>
    </div>
  )
}
