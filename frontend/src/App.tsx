import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppErrorBoundary } from './app/AppErrorBoundary'
import { AppShell } from './app/AppShell'
import { modules } from './app/modules'
import { AuthProvider } from './auth/AuthProvider'
import { useAuth } from './auth/use-auth'
import {
  ChangePasswordPage,
  LoginPage,
  SessionLoadingPage,
  SessionUnavailablePage,
} from './auth/AuthPages'
import { ControlTowerPage } from './features/control-tower/ControlTowerPage'
import { ModulePlaceholder } from './features/placeholders/ModulePlaceholder'
import { ShipmentsPage } from './features/shipments/ShipmentsPage'
import { ShipmentDetailPage } from './features/shipments/ShipmentDetailPage'
import { TrackingPage } from './features/tracking/TrackingPage'
import { AdministrationPage } from './features/admin/AdministrationPage'
import { ReportsPage } from './features/reports/ReportsPage'
import { HubRouteIntelligencePage } from './features/hub-route-intelligence/HubRouteIntelligencePage'
import { GeospatialPage } from './features/geospatial/GeospatialPage'

function AuthenticatedRoutes() {
  const { status, user } = useAuth()

  if (status === 'loading') return <SessionLoadingPage />
  if (status === 'unavailable') return <SessionUnavailablePage />

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  if (user.must_change_password) {
    return (
      <Routes>
        <Route path="/change-password" element={<ChangePasswordPage />} />
        <Route path="*" element={<Navigate to="/change-password" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/control-tower" replace />} />
        <Route path="/login" element={<Navigate to="/control-tower" replace />} />
        <Route path="/change-password" element={<Navigate to="/control-tower" replace />} />
        <Route path="/control-tower" element={<ControlTowerPage />} />
        <Route path="/operations" element={<ShipmentsPage />} />
        <Route path="/operations/:shipmentId" element={<ShipmentDetailPage />} />
        <Route path="/tracking" element={<TrackingPage />} />
        <Route path="/hub-route-intelligence" element={<HubRouteIntelligencePage />} />
        <Route path="/geospatial" element={<GeospatialPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route
          path="/administration"
          element={
            user.roles.includes('ADMIN')
              ? <AdministrationPage />
              : <Navigate to="/control-tower" replace />
          }
        />
        {modules
          .filter((module) => module.status === 'development')
          .map((module) => (
            <Route
              key={module.path}
              path={module.path}
              element={<ModulePlaceholder module={module} />}
            />
          ))}
        <Route path="*" element={<Navigate to="/control-tower" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <AppErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <AuthenticatedRoutes />
        </AuthProvider>
      </BrowserRouter>
    </AppErrorBoundary>
  )
}
