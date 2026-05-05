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
