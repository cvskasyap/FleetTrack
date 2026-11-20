import type { LucideIcon } from 'lucide-react'
import {
  Activity,
  Boxes,
  ChartNoAxesCombined,
  CircleGauge,
  Database,
  FlaskConical,
  MapPinned,
  PackageSearch,
  ScanLine,
  Settings2,
  SlidersHorizontal,
  TriangleAlert,
} from 'lucide-react'

export type AppModule = {
  path: string
  label: string
  description: string
  icon: LucideIcon
  status: 'live' | 'development'
}

export const modules: AppModule[] = [
  {
    path: '/control-tower',
    label: 'Executive control tower',
    description: 'Live operational overview',
    icon: CircleGauge,
    status: 'live',
  },
  {
    path: '/geospatial',
    label: 'Geospatial intelligence',
    description: 'Geographic data quality and network relationships',
    icon: MapPinned,
    status: 'live',
  },
  {
    path: '/operations',
    label: 'Shipment operations',
    description: 'Search shipment register',
    icon: Boxes,
    status: 'live',
  },
  {
    path: '/tracking',
    label: 'Shipment tracking',
    description: 'Relational and event history',
    icon: ScanLine,
    status: 'live',
  },
  {
    path: '/sla-intelligence',
    label: 'Predictive SLA intelligence',
    description: 'Risk scoring and alerts',
    icon: TriangleAlert,
    status: 'development',
  },
  {
    path: '/hub-route-intelligence',
    label: 'Hub & route intelligence',
    description: 'Lane and facility performance',
    icon: ChartNoAxesCombined,
    status: 'live',
  },
  {
    path: '/event-analytics',
    label: 'MongoDB event analytics',
    description: 'Scan aggregation insights',
    icon: Activity,
    status: 'development',
  },
  {
    path: '/data-quality',
    label: 'Data quality monitoring',
    description: 'Integrity and freshness checks',
    icon: Database,
    status: 'development',
  },
  {
    path: '/research-lab',
    label: 'Research & model lab',
    description: 'Experiments and evaluation',
    icon: FlaskConical,
    status: 'development',
  },
  {
    path: '/simulation',
    label: 'Simulation studio',
    description: 'Scenario planning',
    icon: SlidersHorizontal,
    status: 'development',
  },
  {
    path: '/reports',
    label: 'Reports & exports',
    description: 'Download database-backed shipment reports',
    icon: PackageSearch,
    status: 'live',
  },
  {
    path: '/administration',
    label: 'System administration',
    description: 'Services and configuration',
    icon: Settings2,
    status: 'live',
  },
]

export const liveModules = modules.filter((module) => module.status === 'live')
