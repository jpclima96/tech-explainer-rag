import type { FactCheckRequest, FactCheckResponse } from './types'

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export async function postCheck(body: FactCheckRequest): Promise<FactCheckResponse> {
  const res = await fetch(`${BASE_URL}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(120_000),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'unknown_error' }))
    const e = new Error(err.detail ?? 'Request failed')
    ;(e as Error & { status: number }).status = res.status
    throw e
  }

  return res.json()
}
