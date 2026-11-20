import { createContext } from 'react'
import type { AuthUser } from '../lib/contracts'

export const authQueryKey = ['auth', 'current-user'] as const

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated' | 'unavailable'

export type AuthContextValue = {
  user: AuthUser | null
  status: AuthStatus
  error: Error | null
  login: (username: string, password: string) => Promise<AuthUser>
  logout: () => Promise<void>
  changePassword: (currentPassword: string, newPassword: string, confirmPassword: string) => Promise<void>
  retrySession: () => Promise<void>
}

export const AuthContext = createContext<AuthContextValue | null>(null)
