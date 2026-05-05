interface Props {
  error: Error & { status?: number }
  onRetry: () => void
}

const MESSAGES: Record<number, { title: string; body: string }> = {
  504: {
    title: 'Search Timed Out',
    body: 'The service took too long to retrieve sources. Please try again or shorten your text.',
  },
  502: {
    title: 'AI Service Unavailable',
    body: 'The language model could not process your request. This is usually temporary — try again in a moment.',
  },
  422: {
    title: 'Invalid Input',
    body: 'Your text did not meet the requirements (10–50,000 characters). Please check and try again.',
  },
}

export function ErrorMessage({ error, onRetry }: Props) {
  const info = error.status ? MESSAGES[error.status] : undefined
  const title = info?.title ?? 'Something went wrong'
  const body = info?.body ?? 'An unexpected error occurred. Please try again.'

  return (
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-5 space-y-3">
      <div className="flex items-start gap-3">
        <span className="text-red-500 text-xl leading-none mt-0.5">⚠</span>
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
