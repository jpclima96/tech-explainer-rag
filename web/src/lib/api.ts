// API types and client. Mirrors the Pydantic models in fact_checker/models.py.

export type Language = 'en' | 'pt-BR'
export type Classification = 'true' | 'false' | 'misleading' | 'unverifiable'

export interface Source {
  title: string
  url: string
  credibility_score: number
}

export interface Claim {
  claim: string
  classification: Classification
  confidence_score: number
  explanation: string
  sources: Source[]
}

export interface FactCheckRequest {
  text: string
  context?: string
  language?: Language
}

export interface FactCheckResponse {
  claims: Claim[]
  overall_assessment: string
  misinformation_patterns: string[]
  emotional_manipulation_detected: boolean
}

export class ApiError extends Error {
  status: number
  detail: string
  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

const BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export async function checkFacts(req: FactCheckRequest): Promise<FactCheckResponse> {
  const res = await fetch(`${BASE_URL}/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal: AbortSignal.timeout(120_000),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(res.status, body.detail ?? 'Request failed')
  }
  return res.json()
}
