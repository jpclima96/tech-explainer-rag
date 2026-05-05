import { useMutation } from '@tanstack/react-query'
import { postCheck } from '../api/client'
import type { FactCheckRequest, FactCheckResponse } from '../api/types'

export function useFactCheck() {
  return useMutation<FactCheckResponse, Error & { status?: number }, FactCheckRequest>({
    mutationFn: postCheck,
    retry: (count, error) => {
      const status = (error as Error & { status?: number }).status
      if (status === 422 || status === 502 || status === 504) return false
      return count < 1
    },
  })
}
