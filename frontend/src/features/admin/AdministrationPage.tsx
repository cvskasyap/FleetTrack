import { useState } from 'react'
import type { FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { KeyRound, RefreshCw, ShieldCheck, UserCheck, UserPlus, UserX } from 'lucide-react'
import { ApiError, fleetApi } from '../../lib/api'
import type { AdminUser } from '../../lib/contracts'

const usersQueryKey = ['admin', 'users'] as const

function errorText(error: unknown): string {
  if (error instanceof ApiError) return error.message
  return 'The request could not be completed. Try again.'
}

function formatDate(value: string | null): string {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function AdministrationPage() {
  const queryClient = useQueryClient()
  const usersQuery = useQuery({
    queryKey: usersQueryKey,
    queryFn: ({ signal }) => fleetApi.adminUsers(signal),
  })
  const [username, setUsername] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<'ADMIN' | 'USER'>('USER')
  const [temporaryPassword, setTemporaryPassword] = useState('')
  const [actionError, setActionError] = useState('')

  const createUser = useMutation({
    mutationFn: (payload: Parameters<typeof fleetApi.createAdminUser>[0]) =>
      fleetApi.createAdminUser(payload),
    onSuccess: async (result) => {
      setTemporaryPassword(result.temporary_password)
      setUsername('')
      setDisplayName('')
      setEmail('')
      setRole('USER')
      setActionError('')
      await queryClient.invalidateQueries({ queryKey: usersQueryKey })
    },
    onError: (error) => setActionError(errorText(error)),
  })

  const updateUser = useMutation({
    mutationFn: ({ userId, changes }: {
      userId: number
      changes: { roles?: Array<'ADMIN' | 'USER'>; is_active?: boolean }
    }) => fleetApi.updateAdminUser(userId, changes),
    onSuccess: async () => {
      setActionError('')
      await queryClient.invalidateQueries({ queryKey: usersQueryKey })
    },
    onError: (error) => setActionError(errorText(error)),
  })

  const resetPassword = useMutation({
    mutationFn: (userId: number) => fleetApi.resetAdminPassword(userId),
    onSuccess: async (result) => {
      setTemporaryPassword(result.temporary_password)
      setActionError('')
      await queryClient.invalidateQueries({ queryKey: usersQueryKey })
    },
    onError: (error) => setActionError(errorText(error)),
  })

  function submitCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setTemporaryPassword('')
    setActionError('')
    createUser.mutate({
      username: username.trim(),
      display_name: displayName.trim(),
      email: email.trim() || null,
      roles: [role],
    })
  }

  function chooseRole(user: AdminUser, nextRole: 'ADMIN' | 'USER') {
    if (user.roles.length === 1 && user.roles[0] === nextRole) return
    setActionError('')
    updateUser.mutate({ userId: user.user_id, changes: { roles: [nextRole] } })
  }

  function toggleActive(user: AdminUser) {
    setActionError('')
    updateUser.mutate({
      userId: user.user_id,
      changes: { is_active: !user.is_active },
    })
  }

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">PLATFORM</p>
          <h1>System administration</h1>
          <p className="page-description">Manage access with accountable, server-enforced roles.</p>
        </div>
        <span className="admin-protection"><ShieldCheck size={15} /> ADMINISTRATOR ACCESS</span>
      </header>

      <div className="data-notice">
        <ShieldCheck size={14} />
        <span>Account changes are audited. Temporary passwords are displayed once and are never stored in the browser.</span>
      </div>

      {temporaryPassword && (
        <section className="temporary-password" aria-labelledby="temporary-password-title" role="status">
          <div>
            <p className="eyebrow">ONE-TIME CREDENTIAL</p>
            <h2 id="temporary-password-title">Copy this temporary password now</h2>
            <p>The user must choose a new password at their first sign-in. This value disappears when you leave this page.</p>
            <code>{temporaryPassword}</code>
          </div>
          <button className="button button-secondary button-sm" onClick={() => setTemporaryPassword('')} type="button">
            Dismiss
          </button>
        </section>
      )}

      {actionError && <div className="auth-error" role="alert">{actionError}</div>}

      <section className="panel admin-create-panel">
        <div className="panel-heading">
          <div>
            <h2>Create account</h2>
            <p>New accounts receive a one-time password and are required to change it.</p>
          </div>
          <UserPlus size={17} className="admin-heading-icon" />
        </div>
        <form className="admin-create-form" onSubmit={submitCreate}>
          <label>
            Username
            <input autoComplete="off" maxLength={64} minLength={3} onChange={(event) => setUsername(event.target.value)} required value={username} />
          </label>
          <label>
            Display name
            <input autoComplete="off" maxLength={120} onChange={(event) => setDisplayName(event.target.value)} required value={displayName} />
          </label>
          <label>
            Email <span className="optional-label">Optional</span>
            <input autoComplete="off" maxLength={254} onChange={(event) => setEmail(event.target.value)} type="email" value={email} />
          </label>
          <label>
            Role
            <select onChange={(event) => setRole(event.target.value as 'ADMIN' | 'USER')} value={role}>
              <option value="USER">User</option>
              <option value="ADMIN">Administrator</option>
            </select>
          </label>
          <button className="button button-primary admin-create-submit" disabled={createUser.isPending} type="submit">
            <UserPlus size={14} /> {createUser.isPending ? 'Creating…' : 'Create account'}
          </button>
        </form>
      </section>

      <section className="panel admin-users-panel">
        <div className="panel-heading table-heading">
          <div>
            <h2>User accounts</h2>
            <p>Roles and account state are enforced by the backend on every request.</p>
          </div>
          <div className="admin-table-actions">
            <span className="table-count">{usersQuery.data?.total ?? 0} accounts</span>
            <button
              aria-label="Refresh user accounts"
              className="button button-icon"
              disabled={usersQuery.isFetching}
              onClick={() => void usersQuery.refetch()}
              type="button"
            >
              <RefreshCw size={14} />
            </button>
          </div>
        </div>
        {usersQuery.isPending ? (
          <div className="loading-panel" role="status" aria-label="Loading user accounts">
            <span className="skeleton skeleton-wide" />
            <span className="skeleton" />
            <span className="skeleton" />
          </div>
        ) : usersQuery.isError ? (
          <div className="admin-table-state" role="alert">
            <p>User accounts could not be loaded.</p>
            <span>{errorText(usersQuery.error)}</span>
            <button className="button button-secondary button-sm" onClick={() => void usersQuery.refetch()} type="button">
              Try again
            </button>
          </div>
        ) : usersQuery.data.items.length === 0 ? (
          <div className="admin-table-state">No accounts are configured.</div>
        ) : (
          <div className="table-scroll">
            <table className="data-table admin-user-table">
              <thead>
                <tr>
                  <th scope="col">Account</th>
                  <th scope="col">Role</th>
                  <th scope="col">Status</th>
                  <th scope="col">Last sign-in</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {usersQuery.data.items.map((user) => (
                  <tr key={user.user_id}>
                    <td>
                      <strong>{user.display_name}</strong>
                      <span className="cell-subtext">{user.username}{user.email ? ` · ${user.email}` : ''}</span>
                    </td>
                    <td>
                      <label className="sr-only" htmlFor={`role-${user.user_id}`}>Role for {user.username}</label>
                      <select
                        className="admin-role-select"
                        disabled={updateUser.isPending}
                        id={`role-${user.user_id}`}
                        onChange={(event) => chooseRole(user, event.target.value as 'ADMIN' | 'USER')}
                        value={user.roles.includes('ADMIN') ? 'ADMIN' : 'USER'}
                      >
                        <option value="USER">User</option>
                        <option value="ADMIN">Administrator</option>
                      </select>
                    </td>
                    <td>
                      <span className={`admin-account-status ${user.is_active ? 'admin-account-active' : 'admin-account-inactive'}`}>
                        <span /> {user.is_active ? 'Active' : 'Disabled'}
                        {user.must_change_password && <small> · Password reset required</small>}
                      </span>
                    </td>
                    <td>{formatDate(user.last_login_at)}</td>
                    <td>
                      <div className="admin-row-actions">
                        <button
                          className="button button-secondary button-sm"
                          disabled={resetPassword.isPending}
                          onClick={() => {
                            setTemporaryPassword('')
                            resetPassword.mutate(user.user_id)
                          }}
                          type="button"
                        >
                          <KeyRound size={13} /> Reset password
                        </button>
                        <button
                          aria-label={`${user.is_active ? 'Disable' : 'Enable'} ${user.username}`}
                          className="button button-icon"
                          disabled={updateUser.isPending}
                          onClick={() => toggleActive(user)}
                          title={user.is_active ? 'Disable account' : 'Enable account'}
                          type="button"
                        >
                          {user.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
