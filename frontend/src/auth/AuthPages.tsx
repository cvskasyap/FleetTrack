import { useState } from 'react'
import type { FormEvent } from 'react'
import { ArrowRight, ShieldCheck } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../lib/api'
import { useAuth } from './use-auth'

function AuthBrand() {
  return (
    <div className="auth-brand">
      <span className="brand-mark" aria-hidden="true"><span /><span /><span /><span /></span>
      <span><strong>fleettrack</strong><small>LOGISTICS INTELLIGENCE</small></span>
    </div>
  )
}

function AuthFrame({ children }: { children: React.ReactNode }) {
  return (
    <main className="auth-page">
      <section className="auth-panel">
        <AuthBrand />
        {children}
        <p className="auth-footnote">Authorized FleetTrack users only · Synthetic demonstration environment</p>
      </section>
      <aside className="auth-aside" aria-label="FleetTrack platform information">
        <div className="auth-aside-content">
          <span className="auth-aside-kicker"><ShieldCheck size={15} /> CONTROL TOWER ACCESS</span>
          <h1>Operational intelligence, with accountability built in.</h1>
          <p>Secure access to shipment operations, performance insights, and research workflows.</p>
        </div>
        <span className="auth-aside-footer">FLEETTRACK 2.0 · LOGISTICS INTELLIGENCE &amp; CONTROL TOWER</span>
      </aside>
    </main>
  )
}

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const notice = (location.state as { message?: string } | null)?.message

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const user = await login(username.trim(), password)
      navigate(user.must_change_password ? '/change-password' : '/control-tower', { replace: true })
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : 'Sign-in could not be completed. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthFrame>
      <div className="auth-heading">
        <p className="eyebrow">WELCOME BACK</p>
        <h2>Sign in to FleetTrack</h2>
        <p>Use your administrator-provisioned account to continue.</p>
      </div>
      {notice && <div className="auth-notice" role="status">{notice}</div>}
      {error && <div className="auth-error" role="alert">{error}</div>}
      <form className="auth-form" onSubmit={submit}>
        <label>
          Username
          <input
            autoComplete="username"
            autoFocus
            maxLength={64}
            name="username"
            onChange={(event) => setUsername(event.target.value)}
            required
            value={username}
          />
        </label>
        <label>
          Password
          <input
            autoComplete="current-password"
            maxLength={256}
            name="password"
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
        </label>
        <button className="button button-primary auth-submit" disabled={submitting} type="submit">
          {submitting ? 'Signing in…' : 'Sign in'}
          {!submitting && <ArrowRight size={16} />}
        </button>
      </form>
      <p className="auth-security-note">
        Sessions are protected with secure, server-managed credentials. Contact an administrator if you need access.
      </p>
    </AuthFrame>
  )
}

export function ChangePasswordPage() {
  const { changePassword } = useAuth()
  const navigate = useNavigate()
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (newPassword.length < 14) {
      setError('Choose a password with at least 14 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('The new passwords do not match.')
      return
    }
    setSubmitting(true)
    setError('')
    try {
      await changePassword(currentPassword, newPassword, confirmPassword)
      navigate('/login', {
        replace: true,
        state: { message: 'Password updated. Sign in with your new password.' },
      })
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : 'The password could not be changed. Please try again.',
      )
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthFrame>
      <div className="auth-heading">
        <p className="eyebrow">ACCOUNT SECURITY</p>
        <h2>Choose a new password</h2>
        <p>Your administrator issued a temporary password. Replace it before continuing.</p>
      </div>
      {error && <div className="auth-error" role="alert">{error}</div>}
      <form className="auth-form" onSubmit={submit}>
        <label>
          Temporary password
          <input
            autoComplete="current-password"
            onChange={(event) => setCurrentPassword(event.target.value)}
            required
            type="password"
            value={currentPassword}
          />
        </label>
        <label>
          New password
          <input
            autoComplete="new-password"
            minLength={14}
            onChange={(event) => setNewPassword(event.target.value)}
            required
            type="password"
            value={newPassword}
          />
          <small>Use at least 14 characters.</small>
        </label>
        <label>
          Confirm new password
          <input
            autoComplete="new-password"
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
            type="password"
            value={confirmPassword}
          />
        </label>
        <button className="button button-primary auth-submit" disabled={submitting} type="submit">
          {submitting ? 'Updating password…' : 'Update password'}
          {!submitting && <ArrowRight size={16} />}
        </button>
      </form>
    </AuthFrame>
  )
}

export function SessionLoadingPage() {
  return (
    <main className="auth-status-page" role="status">
      <span className="auth-spinner" aria-hidden="true" />
      <p>Verifying your FleetTrack session…</p>
    </main>
  )
}

export function SessionUnavailablePage() {
  const { retrySession } = useAuth()
  const [retrying, setRetrying] = useState(false)

  async function retry() {
    setRetrying(true)
    try {
      await retrySession()
    } finally {
      setRetrying(false)
    }
  }

  return (
    <main className="auth-status-page" role="alert">
      <p className="eyebrow">SESSION SERVICE UNAVAILABLE</p>
      <h1>Could not verify your account</h1>
      <p>FleetTrack could not reach the authentication service. Your session has not been changed.</p>
      <button className="button button-primary" disabled={retrying} onClick={() => void retry()} type="button">
        {retrying ? 'Retrying…' : 'Retry connection'}
      </button>
    </main>
  )
}
