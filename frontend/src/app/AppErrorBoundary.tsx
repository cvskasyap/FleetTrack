import { Component } from 'react'
import type { ReactNode } from 'react'

type AppErrorBoundaryProps = {
  children: ReactNode
}

type AppErrorBoundaryState = {
  hasError: boolean
}

export class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { hasError: false }

  static getDerivedStateFromError(): AppErrorBoundaryState {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="fatal-error-state" role="alert">
          <div>
            <p className="eyebrow">APPLICATION ERROR</p>
            <h1>FleetTrack could not render this view</h1>
            <p>Reload the application to recover. If the problem persists, contact your administrator.</p>
            <button type="button" className="button button-primary" onClick={() => window.location.reload()}>
              Reload application
            </button>
          </div>
        </main>
      )
    }

    return this.props.children
  }
}
