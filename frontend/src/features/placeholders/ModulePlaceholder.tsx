import { ArrowRight, Construction } from 'lucide-react'
import { Link } from 'react-router-dom'
import { liveModules, type AppModule } from '../../app/modules'
import { PageHeader, Panel } from '../../components/ui'

export function ModulePlaceholder({ module }: { module: AppModule }) {
  const Icon = module.icon

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="MODULE ROADMAP"
        title={module.label}
        description={module.description}
      />
      <Panel className="development-panel">
        <div className="development-icon">
          <Icon size={22} strokeWidth={1.7} />
        </div>
        <span className="development-kicker">
          <Construction size={14} />
          In development
        </span>
        <h2>This module is not connected yet</h2>
        <p>
          This area is intentionally an implementation placeholder. The current API does not expose
          the data or workflows required to present this module, so no illustrative metrics or
          simulated results are shown.
        </p>
        <div className="development-next">
          <span>Available data experiences</span>
          {liveModules.map((liveModule) => {
            const LiveIcon = liveModule.icon
            return (
              <Link key={liveModule.path} to={liveModule.path}>
                <LiveIcon size={15} />
                {liveModule.label}
                <ArrowRight size={14} />
              </Link>
            )
          })}
        </div>
      </Panel>
    </div>
  )
}
