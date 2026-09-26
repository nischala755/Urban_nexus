import { useEffect, useRef } from 'react'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { KPI } from './types'

echarts.use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])
export default function Trajectory({ baseline, action, metric = 'waste_fill_pct', unit = '%' }: {
  baseline: KPI[]; action?: KPI[]; metric?: string; unit?: string
}) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    chart.setOption({ animation: false, color: ['#c29353', '#168479'],
      tooltip: { trigger: 'axis', valueFormatter: (value: number) => `${Number(value).toFixed(1)} ${unit}` },
      legend: { bottom: 0, icon: 'roundRect', textStyle: { color: '#657674', fontSize: 11 } },
      grid: { left: 42, top: 16, right: 16, bottom: 48 },
      xAxis: { type: 'category', data: baseline.map(r => r.minute), name: 'min', nameLocation: 'insideEnd',
        axisLabel: { color: '#71817d', interval: 14 }, axisLine: { lineStyle: { color: '#dae2dd' } }, axisTick: { show: false } },
      yAxis: { type: 'value', axisLabel: { color: '#71817d', formatter: `{value}${unit}` }, splitLine: { lineStyle: { color: '#edf0ed' } } },
      series: [{ type: 'line', name: 'No intervention', data: baseline.map(r => r[metric]), symbol: 'none', lineStyle: { type: 'dashed', width: 2 } },
        ...(action ? [{ type: 'line', name: 'With intervention', data: action.map(r => r[metric]), symbol: 'none', lineStyle: { width: 3 }, areaStyle: { opacity: 0.06 } }] : [])],
    })
    const observer = new ResizeObserver(() => chart.resize())
    observer.observe(ref.current)
    return () => { observer.disconnect(); chart.dispose() }
  }, [baseline, action, metric, unit])
  return <div ref={ref} className="trajectory" role="img" aria-label={`${metric} numerical trajectory over simulation minutes`} />
}
