import * as Dialog from '@radix-ui/react-dialog'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  Bell,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Menu,
  Moon,
  Search,
  Sun,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { KeyboardEvent as ReactKeyboardEvent } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useTheme } from './use-theme'
import { modules } from './modules'
import { fleetApi } from '../lib/api'
import type { AppModule } from './modules'
import { useAuth } from '../auth/use-auth'

const navigationGroups = [
  { label: 'WORKSPACE', paths: ['/control-tower', '/geospatial'] },
  { label: 'OPERATIONS', paths: ['/operations', '/tracking'] },
  {
    label: 'INTELLIGENCE',
    paths: ['/sla-intelligence', '/hub-route-intelligence', '/event-analytics', '/data-quality'],
  },
  { label: 'RESEARCH & PLANNING', paths: ['/research-lab', '/simulation', '/reports'] },
  { label: 'PLATFORM', paths: ['/administration'] },
]

function BrandMark() {
  return (
    <span className="brand-mark" aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
    </span>
  )
}

function ServiceHealth() {
  const query = useQuery({
    queryKey: ['health', 'ready'],
    queryFn: ({ signal }) => fleetApi.ready(signal),
    refetchInterval: 30_000,
    retry: false,
  })
  const ready = query.data?.status === 'ready'

  return (
    <div
      className={`service-health ${ready ? 'service-health-ok' : query.isLoading ? 'service-health-pending' : 'service-health-down'}`}
      title={
        query.data
          ? `PostgreSQL: ${query.data.postgres?.status}; MongoDB: ${query.data.mongodb?.status}`
          : 'API and data-service health'
      }
      aria-label={
        query.data
          ? `API services ${ready ? 'ready' : 'not ready'}`
          : query.isLoading
            ? 'Checking services'
            : 'Service health unavailable'
      }
    >
      <span className="service-health-dot" />
      <span>{ready ? 'Systems normal' : query.isLoading ? 'Connecting' : 'Service issue'}</span>
    </div>
  )
}

function CommandPalette({
  open,
  onOpenChange,
  availableModules,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  availableModules: AppModule[]
}) {
  const [searchState, setSearchState] = useState({ open, value: '' })
  const [activeIndex, setActiveIndex] = useState(0)
  const search = searchState.open === open ? searchState.value : ''
  const navigate = useNavigate()
  const filteredModules = useMemo(
    () =>
      availableModules.filter((module) =>
        `${module.label} ${module.description}`.toLowerCase().includes(search.toLowerCase()),
      ),
    [availableModules, search],
  )
  const activeModule = filteredModules[activeIndex]

  function openModule(path: string) {
    navigate(path)
    onOpenChange(false)
  }

  function onSearchKeyDown(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (!filteredModules.length) return

    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((index) => (index + 1) % filteredModules.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((index) => (index - 1 + filteredModules.length) % filteredModules.length)
    } else if (event.key === 'Enter' && activeModule) {
      event.preventDefault()
      openModule(activeModule.path)
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="command-overlay" />
        <Dialog.Content className="command-dialog">
          <Dialog.Title className="sr-only">FleetTrack command search</Dialog.Title>
          <Dialog.Description className="sr-only">
            Search application modules and navigate to a workspace.
          </Dialog.Description>
          <div className="command-search">
            <Search size={18} />
            <input
              autoFocus
              value={search}
              onChange={(event) => {
                setSearchState({ open, value: event.target.value })
                setActiveIndex(0)
              }}
              onKeyDown={onSearchKeyDown}
              placeholder="Search modules and workspaces..."
              aria-label="Search modules and workspaces"
              role="combobox"
              aria-autocomplete="list"
              aria-expanded={open}
              aria-controls="command-results"
              aria-activedescendant={
                activeModule
                  ? `command-option-${activeModule.path.slice(1).replaceAll('/', '-')}`
                  : undefined
              }
            />
            <Dialog.Close asChild>
              <button type="button" className="command-close" aria-label="Close search">
                <X size={16} />
              </button>
            </Dialog.Close>
          </div>
          <div className="command-list">
            <p className="command-label">WORKSPACES</p>
            {filteredModules.length ? (
              <div id="command-results" role="listbox" aria-label="Workspaces">
                {filteredModules.map((module, index) => {
                  const Icon = module.icon
                  return (
                    <button
                      className={`command-item ${index === activeIndex ? 'command-item-active' : ''}`}
                      id={`command-option-${module.path.slice(1).replaceAll('/', '-')}`}
                      key={module.path}
                      type="button"
                      role="option"
                      aria-selected={index === activeIndex}
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => openModule(module.path)}
                    >
                      <span className="command-item-icon">
                        <Icon size={16} />
                      </span>
                      <span>
                        <strong>{module.label}</strong>
                        <small>{module.description}</small>
                      </span>
                      <span className={`command-status command-status-${module.status}`}>
                        {module.status === 'live' ? 'LIVE' : 'ROADMAP'}
                      </span>
                    </button>
                  )
                })}
              </div>
            ) : (
              <div id="command-results" className="command-empty" role="status">
                No workspace matches that search.
              </div>
            )}
          </div>
          <div className="command-footer">
            <span><kbd>↑</kbd><kbd>↓</kbd> to navigate</span>
            <span><kbd>esc</kbd> to close</span>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

function Sidebar({
  collapsed,
  mobileOpen,
  onToggle,
  onClose,
  availableModules,
}: {
  collapsed: boolean
  mobileOpen: boolean
  onToggle: () => void
  onClose: () => void
  availableModules: AppModule[]
}) {
  const effectiveCollapsed = collapsed && !mobileOpen

  return (
    <>
      {mobileOpen && (
        <button
          type="button"
          className="mobile-sidebar-backdrop"
          onClick={onClose}
          aria-label="Close navigation"
        />
      )}
      <aside
        className={`sidebar ${effectiveCollapsed ? 'sidebar-collapsed' : ''} ${mobileOpen ? 'sidebar-mobile-open' : ''}`}
      >
        <div className="sidebar-brand">
          <Link to="/control-tower" className="brand-lockup" aria-label="FleetTrack control tower">
            <BrandMark />
            {!collapsed && (
              <span className="brand-wordmark">
                <strong>fleettrack</strong>
                <small>INTELLIGENCE</small>
              </span>
            )}
          </Link>
          <button
            type="button"
            className="sidebar-collapse"
            onClick={onToggle}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={15} /> : <ChevronLeft size={15} />}
          </button>
        </div>
        <div className="workspace-switcher">
          <span className="workspace-avatar">F</span>
          {!collapsed && (
            <span className="workspace-label">
              <strong>FleetTrack Demo</strong>
              <small>Synthetic workspace</small>
            </span>
          )}
          {!collapsed && <ChevronDown size={14} className="workspace-chevron" />}
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navigationGroups.map((group) => (
            <div className="nav-group" key={group.label}>
              {!collapsed && <p className="nav-group-label">{group.label}</p>}
              {group.paths.map((path) => {
                const module = availableModules.find((item) => item.path === path)
                if (!module) return null
                const Icon = module.icon
                return (
                  <NavLink
                    key={module.path}
                    to={module.path}
                    onClick={onClose}
                    title={collapsed ? module.label : undefined}
                    className={({ isActive }) => `nav-link ${isActive ? 'nav-link-active' : ''}`}
                    end={module.path === '/control-tower'}
                  >
                    <Icon size={17} strokeWidth={1.8} />
                    {!collapsed && <span>{module.label}</span>}
                    {!collapsed && module.status === 'development' && (
                      <span className="nav-soon">SOON</span>
                    )}
                  </NavLink>
                )
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-data-note">
            <span className="notice-dot" />
            {!collapsed && <span>Synthetic data environment</span>}
          </div>
          {!collapsed && <span className="sidebar-version">FLEETTRACK 2.0 · PREVIEW</span>}
        </div>
      </aside>
    </>
  )
}

function Topbar({
  onOpenSearch,
  onOpenMobileNav,
}: {
  onOpenSearch: () => void
  onOpenMobileNav: () => void
}) {
  const { theme, toggleTheme } = useTheme()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [logoutError, setLogoutError] = useState('')
  const location = useLocation()
  const module = modules.find(
    (item) => location.pathname === item.path || location.pathname.startsWith(`${item.path}/`),
  )
  const initials = user?.display_name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase() ?? 'FT'

  async function signOut() {
    setLogoutError('')
    try {
      await logout()
      navigate('/login', { replace: true })
    } catch {
      setLogoutError('Sign out could not reach the service. Please retry.')
    }
  }

  return (
    <header className="topbar">
      <div className="topbar-leading">
        <button
          type="button"
          className="mobile-menu-button"
          onClick={onOpenMobileNav}
          aria-label="Open navigation"
        >
          <Menu size={19} />
        </button>
        <div className="breadcrumbs">
          <span>Workspace</span>
          <ChevronRight size={14} />
          <strong>{module?.label ?? 'Control tower'}</strong>
        </div>
      </div>
      <div className="topbar-actions">
        <ServiceHealth />
        <button
          type="button"
          className="command-trigger"
          onClick={onOpenSearch}
          aria-label="Search FleetTrack"
        >
          <Search size={15} />
          <span>Search anything</span>
          <kbd>⌘ K</kbd>
        </button>
        <button
          type="button"
          className="topbar-icon-button theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button type="button" className="topbar-icon-button notification-trigger" aria-label="Notifications">
              <Bell size={17} />
              <span className="sr-only">Notifications</span>
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content className="dropdown-content notification-content" align="end" sideOffset={10}>
              <div className="dropdown-heading">
                <strong>Notifications</strong>
                <span>Service status</span>
              </div>
              <div className="notification-empty">
                <Activity size={17} />
                <p>No alert feed is connected yet.</p>
                <span>Service readiness is shown in the command bar.</span>
              </div>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button type="button" className="account-trigger" aria-label="Account menu">
              <span className="account-avatar">{initials}</span>
              <ChevronDown size={14} />
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content className="dropdown-content account-content" align="end" sideOffset={10}>
              <div className="account-summary">
                <span className="account-avatar account-avatar-large">{initials}</span>
                <span>
                  <strong>{user?.display_name}</strong>
                  <small>{user?.username} · {user?.roles.join(', ')}</small>
                </span>
              </div>
              <DropdownMenu.Separator className="dropdown-separator" />
              <DropdownMenu.Item className="dropdown-item" onSelect={toggleTheme}>
                {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                Switch to {theme === 'dark' ? 'light' : 'dark'} appearance
              </DropdownMenu.Item>
              {logoutError && <p className="account-error" role="alert">{logoutError}</p>}
              <DropdownMenu.Item
                className="dropdown-item"
                onSelect={(event) => {
                  event.preventDefault()
                  void signOut()
                }}
              >
                <LogOut size={15} />
                Sign out
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  )
}

export function AppShell() {
  const { user } = useAuth()
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const availableModules = useMemo(
    () => modules.filter((module) => module.path !== '/administration' || user?.roles.includes('ADMIN')),
    [user],
  )

  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
      if (event.key === 'Escape') setMobileOpen(false)
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <div className="app-shell">
      <Sidebar
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onToggle={() => setCollapsed((value) => !value)}
        onClose={() => setMobileOpen(false)}
        availableModules={availableModules}
      />
      <div className={`app-main ${collapsed ? 'main-sidebar-collapsed' : ''}`}>
        <Topbar
          onOpenSearch={() => setSearchOpen(true)}
          onOpenMobileNav={() => setMobileOpen(true)}
        />
        <main className="main-content">
          <Outlet />
        </main>
        <footer className="app-footer">
          <span><BrandMark /> FleetTrack Intelligence</span>
          <span>Demonstration environment · Synthetic records</span>
        </footer>
      </div>
      <CommandPalette
        open={searchOpen}
        onOpenChange={setSearchOpen}
        availableModules={availableModules}
      />
    </div>
  )
}
