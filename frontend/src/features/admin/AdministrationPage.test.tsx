import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fleetApi } from '../../lib/api'
import { AdministrationPage } from './AdministrationPage'

vi.mock('../../lib/api', () => ({
  ApiError: class ApiError extends Error {
    readonly status: number

    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  },
  fleetApi: {
    adminUsers: vi.fn(),
    createAdminUser: vi.fn(),
    updateAdminUser: vi.fn(),
    resetAdminPassword: vi.fn(),
  },
}))

const existingUser = {
  user_id: 7,
  username: 'operator',
  display_name: 'Fleet Operator',
  email: null,
  is_active: true,
  must_change_password: false,
  roles: ['USER'] as Array<'ADMIN' | 'USER'>,
  created_at: '2026-01-10T12:00:00Z',
  last_login_at: null,
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <AdministrationPage />
    </QueryClientProvider>,
  )
}

describe('system administration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(fleetApi.adminUsers).mockResolvedValue({
      total: 1,
      items: [existingUser],
    })
    vi.mocked(fleetApi.createAdminUser).mockResolvedValue({
      user: {
        ...existingUser,
        user_id: 8,
        username: 'new.operator',
        display_name: 'New Operator',
        must_change_password: true,
      },
      temporary_password: 'one-time-secret-from-api',
    })
  })

  it('shows current accounts and the one-time password returned by the API', async () => {
    renderPage()

    expect(await screen.findByText('Fleet Operator')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Username'), { target: { value: 'new.operator' } })
    fireEvent.change(screen.getByLabelText('Display name'), { target: { value: 'New Operator' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create account' }))

    expect(await screen.findByText('one-time-secret-from-api')).toBeInTheDocument()
    expect(fleetApi.createAdminUser).toHaveBeenCalledWith({
      username: 'new.operator',
      display_name: 'New Operator',
      email: null,
      roles: ['USER'],
    })
    expect(screen.getByText(/must choose a new password at their first sign-in/i)).toBeInTheDocument()
  })
})
