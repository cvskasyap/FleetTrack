import ReactEChartsCore from 'echarts-for-react/lib/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import * as echarts from 'echarts/core'
import type { EChartsOption } from 'echarts'
import { CanvasRenderer } from 'echarts/renderers'
import { useTheme } from '../app/use-theme'
import type { HubPerformance, MonthlyTrend, RoutePerformance } from '../lib/contracts'
import { formatMonth } from '../lib/utils'

echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

function chartPalette(theme: 'dark' | 'light') {
  return theme === 'dark'
    ? {
        text: '#a3adba',
        axis: '#343e4a',
        grid: '#202a35',
        tooltip: '#131b24',
        tooltipBorder: '#303b47',
      }
    : {
        text: '#697586',
        axis: '#d8dee7',
        grid: '#edf0f4',
        tooltip: '#ffffff',
        tooltipBorder: '#dce2e9',
      }
}

function useBaseOption() {
  const { theme } = useTheme()
  const palette = chartPalette(theme)

  return {
    animationDuration: 450,
    textStyle: { fontFamily: 'Inter, ui-sans-serif, system-ui, sans-serif' },
    grid: { top: 26, right: 18, bottom: 20, left: 8, containLabel: true },
    tooltip: {
      trigger: 'axis' as const,
      backgroundColor: palette.tooltip,
      borderColor: palette.tooltipBorder,
      textStyle: { color: theme === 'dark' ? '#e5eaf0' : '#1d2938', fontSize: 12 },
      padding: [10, 12],
    },
    xAxis: {
      type: 'category' as const,
      axisLine: { lineStyle: { color: palette.axis } },
      axisTick: { show: false },
      axisLabel: { color: palette.text, fontSize: 11 },
    },
    yAxis: {
      type: 'value' as const,
      minInterval: 1,
      axisLabel: { color: palette.text, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: palette.grid, type: 'dashed' as const } },
    },
    legend: {
      top: 0,
      right: 4,
      itemWidth: 8,
      itemHeight: 8,
      textStyle: { color: palette.text, fontSize: 11 },
    },
  }
}

export function BookingTrendChart({ items }: { items: MonthlyTrend[] }) {
  const base = useBaseOption()
  const option: EChartsOption = {
    ...base,
    color: ['#78a9ff', '#64d8b1'],
    xAxis: {
      ...base.xAxis,
      data: items.map((item) => formatMonth(item.month)),
    },
    series: [
      {
        name: 'Booked',
        type: 'bar',
        barMaxWidth: 20,
        itemStyle: { borderRadius: [3, 3, 0, 0] },
        data: items.map((item) => item.booked_count),
      },
      {
        name: 'Delivered cohort',
        type: 'line',
        smooth: 0.25,
        symbolSize: 6,
        lineStyle: { width: 2 },
        data: items.map((item) => item.delivered_in_booking_cohort),
      },
    ],
  }

  return <ReactEChartsCore echarts={echarts} option={option} notMerge lazyUpdate style={{ height: 276 }} />
}

export function DeliveryEventChart({ items }: { items: MonthlyTrend[] }) {
  const base = useBaseOption()
  const option: EChartsOption = {
    ...base,
    color: ['#edb86a'],
    tooltip: {
      ...base.tooltip,
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        return `${point.axisValue}<br/><strong>${point.value}</strong> shipments delivered`
      },
    },
    xAxis: {
      ...base.xAxis,
      data: items.map((item) => formatMonth(item.month)),
    },
    series: [
      {
        name: 'Delivered by event month',
        type: 'line',
        smooth: 0.22,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 2.5 },
        areaStyle: { opacity: 0.08 },
        data: items.map((item) => item.delivered_at_count),
      },
    ],
  }

  return <ReactEChartsCore echarts={echarts} option={option} notMerge lazyUpdate style={{ height: 276 }} />
}

export function HubVolumeChart({ items }: { items: HubPerformance[] }) {
  const base = useBaseOption()
  const labels = items.map((item) => `${item.hub_code} · ${item.hub_name}`)
  const option: EChartsOption = {
    ...base,
    color: ['#78a9ff'],
    grid: { ...base.grid, left: 18, right: 24 },
    tooltip: {
      ...base.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const item = items[point.dataIndex]
        return item
          ? `${item.hub_name}<br/><strong>${item.shipments_handled}</strong> shipments handled<br/>${item.scan_count} status events`
          : ''
      },
    },
    xAxis: {
      ...base.yAxis,
      type: 'value',
      minInterval: 1,
    },
    yAxis: {
      ...base.xAxis,
      type: 'category',
      data: labels,
    },
    series: [
      {
        name: 'Shipments handled',
        type: 'bar',
        barMaxWidth: 18,
        itemStyle: { borderRadius: [0, 3, 3, 0] },
        data: items.map((item) => item.shipments_handled),
      },
    ],
  }

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ height: Math.max(280, items.length * 28) }}
    />
  )
}

export function RouteOnTimeChart({ items }: { items: RoutePerformance[] }) {
  const base = useBaseOption()
  const option: EChartsOption = {
    ...base,
    color: ['#64d8b1'],
    grid: { ...base.grid, left: 12, right: 30 },
    tooltip: {
      ...base.tooltip,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = Array.isArray(params) ? params[0] : params
        const item = items[point.dataIndex]
        if (!item) return ''
        const rate = item.on_time_pct === null ? 'No SLA results' : `${item.on_time_pct.toFixed(1)}%`
        return `${item.route_code} · ${item.route_name}<br/><strong>${rate}</strong> on time<br/>${item.delivered_shipments} delivered`
      },
    },
    xAxis: {
      ...base.yAxis,
      type: 'value',
      min: 0,
      max: 100,
      axisLabel: { ...base.yAxis.axisLabel, formatter: '{value}%' },
    },
    yAxis: {
      ...base.xAxis,
      type: 'category',
      data: items.map((item) => item.route_code),
    },
    series: [
      {
        name: 'On-time delivery',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: { borderRadius: [0, 3, 3, 0] },
        data: items.map((item) => item.on_time_pct),
      },
    ],
  }

  return (
    <ReactEChartsCore
      echarts={echarts}
      option={option}
      notMerge
      lazyUpdate
      style={{ height: Math.max(300, items.length * 27) }}
    />
  )
}
