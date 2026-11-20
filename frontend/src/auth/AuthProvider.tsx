import type { ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, fleetApi } from '../lib/api'
import { AuthContext, authQueryKey } from './auth-context'
import type { AuthContextValue } from './auth-context'

async function clearPrivateQueries(queryClient: ReturnType<typeof useQueryClient>) {
  await queryClient.cancelQueries()
  queryClient.removeQueries({
    predicate: (query) =>
      query.queryKey[0] !== authQueryKey[0] || query.queryKey[1] !== authQueryKey[1],
  })
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const sessionQuery = useQuery({
    queryKey: authQueryKey,
    queryFn: async ({ signal }) => {
      try {
        return await fleetApi.currentUser(signal)
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null
        throw error
      }
    },
    retry: false,
    staleTime: 0,
    refetchInterval: 5 * 60_000,
    refetchOnWindowFocus: true,
  })

  const value: AuthContextValue = {
    user: sessionQuery.data ?? null,
    status: sessionQuery.isPending
      ? 'loading'
      : sessionQuery.data
        ? 'authenticated'
        : sessionQuery.isError
          ? 'unavailable'
          : 'unauthenticated',
    error: sessionQuery.error instanceof Error ? sessionQuery.error : null,
    login: async (username, password) => {
      const user = await fleetApi.login(username, password)
      await clearPrivateQueries(queryClient)
      queryClient.setQueryData(authQueryKey, user)
      return user
    },
    logout: async () => {
      try {
        await fleetApi.logout()
      } catch (error) {
        if (!(error instanceof ApiError && error.status === 401)) throw error
      }
      await clearPrivateQueries(queryClient)
      queryClient.setQueryData(authQueryKey, null)
    },
    changePassword: async (currentPassword, newPassword, confirmPassword) => {
      await fleetApi.changePassword(currentPassword, newPassword, confirmPassword)
      await clearPrivateQueries(queryClient)
      queryClient.setQueryData(authQueryKey, null)
    },
    retrySession: async () => {
      await sessionQuery.refetch()
    },
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
