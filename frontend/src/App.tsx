import { useCallback, useEffect, useState } from 'react'
import { Activity, ArrowDown, ArrowRight, Check, CheckCircle2, ChevronRight, CircleDot, Download,
  Droplets, FileCheck2, GitBranch, Layers3, Leaf, Loader2, Play, RotateCcw, ShieldCheck,
  SlidersHorizontal, TrafficCone, Truck, X, Zap } from 'lucide-react'
import { api } from './api'
import WardMap from './WardMap'
import Trajectory from './Trajectory'
import type { Action, Decision, Evaluation, Health, Passport, Prediction, Road, StateResponse, Stress } from './types'

const initialBudget = { traffic_delay_max_delta: 3, energy_demand_max_delta: 2, water_reservoir_min: 40,
  waste_overflow_max: 0.1, cost_max: 5000, emissions_proxy_max: 30, route_duration_max: 60 }
const initialWeights = { cost: 0.4, time: 0.3, traffic: 0.2, emissions: 0.1 }
const fmt = (value: number | undefined, places = 1) => value === undefined ? '—' : value.toLocaleString('en-IN', { maximumFractionDigits: places })
const pct = (value: number | undefined) => value === undefined ? '—' : value < 0.001 ? '<0.1%' : `${fmt(value * 100)}%`
const names: Record<string, string> = { traffic_delay: 'Traffic delay increase', energy_demand: 'Energy demand increase',
  reservoir: 'Minimum reservoir', waste_overflow: 'Overflow probability', cost: 'Operating cost', emissions_proxy: 'Emissions proxy', route_duration: 'Route duration' }

function exportJSON(value: unknown, name: string) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: 'application/json' }))
  const anchor = document.createElement('a'); anchor.href = url; anchor.download = name; anchor.click(); URL.revokeObjectURL(url)
}

export default function App() {
  const [current, setCurrent] = useState<StateResponse | null>(null)
  const [health, setHealth] = useState<Health | null>(null)
  const [roads, setRoads] = useState<Road[]>([])
  const [predictions, setPredictions] = useState<Prediction[]>([])
  const [zone, setZone] = useState('Z04')
  const [budget, setBudget] = useState(initialBudget)
  const [weights, setWeights] = useState(initialWeights)
  const [scenario, setScenario] = useState('combined')
  const [severity, setSeverity] = useState(1)
  const [duration, setDuration] = useState(60)
  const [seed, setSeed] = useState(42)
  const [affected, setAffected] = useState(['Z01', 'Z02', 'Z03', 'Z04'])
  const [stress, setStress] = useState<Stress | null>(null)
  const [decision, setDecision] = useState<Decision | null>(null)
  const [preview, setPreview] = useState<Evaluation | null>(null)
  const [passport, setPassport] = useState<Passport | null>(null)
  const [archive, setArchive] = useState<Passport[]>([])
  const [operator, setOperator] = useState('Ward operator')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [labActions, setLabActions] = useState<Action[]>([])
  const [labAction, setLabAction] = useState('')
  const [metric, setMetric] = useState('waste_fill_pct')

  const refresh = useCallback(async () => {
    const [s, h, net, p, a] = await Promise.all([
      api<StateResponse>('/api/v1/state/current'), api<Health>('/health'),
      api<{ roads: Road[] }>('/api/v1/zones'), api<Prediction[]>('/api/v1/predictions'),
      api<Passport[]>('/api/v1/action-passports'),
    ])
    setCurrent(s); setHealth(h); setRoads(net.roads); setPredictions(p); setArchive(a)
  }, [])
  useEffect(() => { refresh().catch(e => setError(`Cannot reach the backend: ${e.message}`)) }, [refresh])
  useEffect(() => {
    api<{ domain_actions: Action[] }>('/api/v1/interventions/candidates', { zone_id: zone })
      .then(r => { setLabActions(r.domain_actions); setLabAction(r.domain_actions[0]?.id ?? '') })
      .catch(e => setError(e.message))
  }, [zone, current?.version])

  const work = async (label: string, task: () => Promise<void>) => {
    if (busy) return
    setBusy(label); setError(''); setNotice('')
    try { await task() } catch (e) { setError(e instanceof Error ? e.message : String(e)) }
    finally { setBusy('') }
  }
  const clearDecision = () => { setDecision(null); setPreview(null); setPassport(null) }
  const selectZone = useCallback((id: string) => { setZone(id); setDecision(null); setPreview(null); setPassport(null) }, [])
  const request = () => ({ zone_id: zone, horizon_minutes: duration, seed, budget, weights })
  const runStress = () => work('Simulating stress', async () => {
    const result = await api<Stress>('/api/v1/stress-tests/run', { scenario, severity, duration_minutes: duration, seed, affected_zones: affected })
    setStress(result); clearDecision(); await refresh()
    setNotice('Stress applied to a fresh synthetic ward. Review the forecast, then search for an intervention.')
  })
  const evaluate = () => work('Evaluating candidates', async () => {
    const result = await api<Decision>('/api/v1/interventions/minimum-effective', request())
    setDecision(result); setPreview(result.selected); setPassport(result.passport); await refresh()
  })
  const decide = (approve: boolean) => work(approve ? 'Checking and simulating action' : 'Recording rejection', async () => {
    if (!passport) return
    const result = await api<Passport>(`/api/v1/action-passports/${passport.id}/${approve ? 'approve' : 'reject'}`, { operator, note })
    setPassport(result); await refresh()
    setNotice(approve ? 'Approved and simulated. The ward state and audit trail are updated.' : 'Recommendation rejected. The ward state is unchanged.')
  })

  const selectedZone = current?.state.zones.find(z => z.id === zone)
  const predictedZone = predictions.find(p => p.zone_id === zone)
  const alerts = predictions.flatMap(p => p.alerts.map(a => ({ ...a, zone_id: p.zone_id })))
  const kpi = current?.kpis
  const isPreviewAlternative = preview && passport && preview.action.id !== passport.proposed_intervention.id
  const noSafe = decision?.status === 'NO SAFE ACTION FOUND'
  const activeConstraints = preview?.budget.constraints ?? []
  const projected = decision?.baseline.kpis
  const timeline = decision?.baseline.series ?? stress?.trajectory ?? []
  const approved = passport?.approval_status === 'approved'

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#overview"><div className="brand-symbol"><GitBranch size={23} /></div><span>urban<span className="brand-light">nexus</span><small>CONNECTED CITY INTELLIGENCE</small></span></a>
      <div className="workspace-label">OPERATIONS WORKSPACE</div>
      <nav>
        <a className="nav-link active" href="#overview"><Layers3 size={18} />Command center<span className="nav-dot" /></a>
        <a className="nav-link" href="#stress"><Activity size={18} />City stress test</a>
        <a className="nav-link" href="#arena"><GitBranch size={18} />Decision arena</a>
        <a className="nav-link" href="#passport"><FileCheck2 size={18} />Action passports<span className="nav-count">{archive.length}</span></a>
        <a className="nav-link" href="#budget"><SlidersHorizontal size={18} />Impact budget</a>
      </nav>
      <div className="sidebar-note"><div className="small-caps">THE OPERATING PRINCIPLE</div><p>The smallest action.<br />A safer urban outcome.</p><div className="sidebar-line" /><span>One ward · Four connected services</span></div>
      <div className="sidebar-bottom"><span className="status-dot" />LOCAL PROTOTYPE<small>Synthetic data only<br />Human approval required</small></div>
    </aside>

    <main id="overview"><fieldset className="workspace-controls" disabled={!!busy} aria-label="Command center controls">
      <header className="topbar"><div className="breadcrumb">Operations <ChevronRight size={13} /><b>Representative ward</b></div>
        <div className="topbar-right"><span className="source-tag"><CircleDot size={12} /> SIMULATED SENSOR FEED</span><span className="operator-avatar">WO</span></div></header>
      <div className="content">
        <section className="page-title"><div><div className="eyebrow">WARD-LEVEL DECISION SUPPORT</div><h1>Command center<span className="live-dot" /></h1><p>Understand the ripple. Find the minimum. Keep the operator in control.</p></div>
          <div className="sim-clock"><span>SIMULATION CLOCK · UTC</span><b>{current ? new Date(current.state.timestamp).toLocaleTimeString('en-GB', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit' }) : '--:--'}<small> t + {fmt(current?.state.elapsed_minutes, 0)} min</small></b><div>Seed {current?.state.metadata.seed ?? 42} · {current?.state.metadata.scenario.replaceAll('_', ' ') ?? 'connecting'}</div></div>
        </section>

        {error && <div className="banner danger" role="alert"><X size={17} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={15} /></button></div>}
        {notice && <div className="banner success" role="status"><CheckCircle2 size={17} /><span>{notice}</span></div>}
        <div className="model-status"><span><span className="status-dot amber" />Reference simulation active</span><span>MATLAB / Simulink: {health?.capabilities.matlab_simulink ?? 'checking availability'}</span><details><summary>Model status</summary><p>{health?.capabilities.sumo}</p><p>{health?.capabilities.traffic}</p><p>No real infrastructure is connected.</p></details></div>

        <section className="kpi-grid" aria-label="Current service KPIs">
          <Kpi icon={<TrafficCone size={19} />} title="TRAFFIC & MOBILITY" value={fmt(kpi?.traffic_delay_seconds)} unit="sec" detail="Current mean delay" color="orange" footer={`${fmt(kpi?.queue_vehicles, 0)} vehicles queued`} />
          <Kpi icon={<Zap size={19} />} title="SMART ENERGY" value={fmt((kpi?.energy_demand_kw ?? 0) / 1000, 2)} unit="MW" detail="Current municipal demand" color="yellow" footer={`${fmt(kpi?.pump_kw, 0)} kW from water pumping`} />
          <Kpi icon={<Droplets size={19} />} title="SMART WATER" value={fmt(kpi?.reservoir_min_pct)} unit="%" detail="Lowest reservoir level" color="blue" footer={`${fmt((kpi?.reservoir_min_pct ?? 0) - budget.water_reservoir_min)} points above safety floor`} />
          <Kpi icon={<Truck size={19} />} title="INTELLIGENT WASTE" value={fmt(selectedZone?.waste.fill_pct)} unit="%" detail={`${zone} current bin fill`} color="green" footer={`${pct(predictedZone?.waste_overflow_probability)} overflow risk in 60 min`} />
        </section>

        <div className="main-grid">
          <div className="main-column">
            <section className="panel map-panel">
              <div className="panel-heading"><div><h2>Connected ward <span className="subtle-tag">04 ZONES</span></h2><p>Service state and intervention footprint</p></div><span className="legend"><i className="legend-dot" />Normal<i className="legend-dot warning" />High fill</span></div>
              <WardMap zones={current?.state.zones ?? []} roads={roads} route={preview?.action.route ?? []} selected={zone} onSelect={busy ? () => {} : selectZone} />
              <div className="map-footer"><span><Layers3 size={13} />Synthetic schematic · not geographic</span><span>Inspect zone <select aria-label="Target zone" value={zone} onChange={e => selectZone(e.target.value)}>{(current?.state.zones ?? []).map(z => <option key={z.id} value={z.id}>{z.id}</option>)}</select></span></div>
            </section>

            <section className="panel stress-panel" id="stress">
              <div className="panel-heading"><div className="heading-icon"><Activity size={19} /><div><h2>City stress test</h2><p>A controlled disturbance. A measurable cascade.</p></div></div><span className="subtle-tag">REPRODUCIBLE</span></div>
              <div className="stress-controls"><label>Scenario<select value={scenario} onChange={e => setScenario(e.target.value)}><option value="combined">Peak-Hour Urban Stress</option><option value="traffic_surge">Traffic surge</option><option value="water_surge">Water-demand surge</option><option value="energy_peak">Energy peak</option><option value="waste_surge">Waste generation surge</option><option value="pump_outage">Pump outage</option><option value="vehicle_failure">Waste vehicle failure</option></select></label>
                <label>Severity <b>{severity.toFixed(1)}×</b><input aria-label="Stress severity" type="range" min="0.1" max="3" step="0.1" value={severity} onChange={e => setSeverity(+e.target.value)} /></label>
                <label>Duration (min)<input type="number" min="15" max="180" value={duration} onChange={e => { setDuration(+e.target.value); clearDecision() }} /></label>
                <label>Seed<input type="number" min="0" value={seed} onChange={e => { setSeed(+e.target.value); clearDecision() }} /></label>
              </div>
              <div className="stress-bottom"><div className="zone-checks"><span>Affected</span>{['Z01', 'Z02', 'Z03', 'Z04'].map(id => <label key={id}><input type="checkbox" checked={affected.includes(id)} onChange={() => setAffected(v => v.includes(id) ? v.filter(x => x !== id) : [...v, id])} />{id}</label>)}</div><button className="secondary compact" disabled={!!busy} onClick={() => work('Resetting ward', async () => { await api('/api/v1/state/reset', { seed }); setStress(null); clearDecision(); await refresh() })}><RotateCcw size={13} />Reset</button><button className="primary compact" disabled={!!busy || !affected.length} onClick={runStress}><Play size={13} />Run stress test</button></div>
              {stress && <div className="stress-result"><span>Degradation: <b>{stress.time_to_degradation_minutes === null ? 'not within horizon' : `${stress.time_to_degradation_minutes} min`}</b></span><span>Services affected: <b>{stress.affected_services.length} / 4</b></span><span>Unassisted recovery: <b>{stress.recovery_estimate_minutes === null ? '>120 min / unresolved' : `${stress.recovery_estimate_minutes} min`}</b></span></div>}
            </section>

            <section className="panel" id="arena">
              <div className="panel-heading"><div><h2>Decision arena <span className="subtle-tag">MINIMUM EFFECTIVE INTERVENTION</span></h2><p>Hard constraints first. Resources second. Preferences third.</p></div><button className="primary" disabled={!!busy || !current} onClick={evaluate}>{busy === 'Evaluating candidates' ? <Loader2 className="spin" size={15} /> : <GitBranch size={15} />}Find minimum intervention</button></div>
              {noSafe ? <div className="no-safe" role="status"><ShieldCheck size={30} /><h3>NO SAFE ACTION FOUND</h3><p>Every effective candidate violates at least one configured constraint.</p><div className="rejection-tags">{Object.entries(decision.rejection_summary).map(([name, count]) => <span key={name}>{names[name] ?? name.replaceAll('_', ' ')} · {count}</span>)}</div><p>Review the limits, add capacity, or escalate to the operator. No passport has been issued.</p></div>
                : decision ? <><div className="arena-summary"><span><CheckCircle2 size={15} />{decision.feasible_count} feasible / {decision.evaluations.length} evaluated</span><span>Target: overflow risk &lt; {pct(budget.waste_overflow_max)}</span></div><div className="plan-grid">{decision.alternatives.map((a, index) => {
                  const plan = decision.evaluations.find(e => e.action.id === a.action_id)!
                  const isMinimum = decision.selected?.action.id === a.action_id
                  return <button className={`plan-card ${preview?.action.id === a.action_id ? 'selected' : ''}`} key={a.action_id} onClick={() => setPreview(plan)}>
                    <div className="plan-top"><span>PLAN {String.fromCharCode(65 + index)}</span>{isMinimum ? <span className="minimum-tag"><Check size={11} />MINIMUM</span> : <span className="safe-text">FEASIBLE</span>}</div>
                    <h3>{plan.action.vehicles} vehicle{plan.action.vehicles !== 1 ? 's' : ''}<small>{plan.action.route.join(' → ') || 'Continue operations'}</small></h3>
                    <div className="plan-metrics"><div><b>{pct(plan.simulation.kpis.overflow_probability)}</b><small>overflow risk</small></div><div><b>₹{fmt(plan.simulation.kpis.cost_inr, 0)}</b><small>operating cost</small></div><div><b>{fmt(plan.simulation.kpis.response_minutes, 0)}m</b><small>response</small></div></div><p>{a.objectives.join(' · ')}</p>
                  </button>
                })}</div></> : <div className="empty-state"><GitBranch size={27} /><h3>From a problem to a defensible action</h3><p>Run a stress test, then evaluate candidate routes against your impact budget.</p><div className="flow-hint">Predict <ArrowRight size={13} /> Simulate <ArrowRight size={13} /> Check <ArrowRight size={13} /> Recommend</div></div>}
              {decision && <details className="candidate-details"><summary>Inspect all {decision.evaluations.length} candidates and rejection reasons</summary><div className="table-scroll"><table><thead><tr><th>Candidate</th><th>Risk</th><th>Gate</th><th>Failed constraints</th></tr></thead><tbody>{decision.evaluations.map(e => <tr key={e.action.id}><td>{e.action.label}</td><td>{pct(e.simulation.kpis.overflow_probability)}</td><td className={e.budget.passed ? 'safe-text' : 'danger-text'}>{e.budget.passed ? 'PASS' : 'FAIL'}</td><td>{e.budget.constraints.filter(c => c.status === 'FAIL').map(c => names[c.name] ?? c.name).join(', ') || 'None'}</td></tr>)}</tbody></table></div></details>}
            </section>

            <section className="panel" id="ripple"><div className="panel-heading"><div><h2>Urban Ripple</h2><p>Trace the action through the services it affects.</p></div>{preview && <span className="subtle-tag">{isPreviewAlternative ? 'ALTERNATIVE PREVIEW' : 'RECOMMENDED PLAN'}</span>}</div>
              {preview && decision ? <><div className="ripple-path"><div className="ripple-problem"><small>PROBLEM</small><b>{pct(projected?.overflow_probability)}</b><span>projected overflow risk</span></div><ArrowRight size={18} /><div><small>INTERVENTION</small><b>{preview.action.vehicles} EV dispatch</b><span>{preview.action.route.slice(1).join(' → ') || 'No route'}</span></div><ArrowRight size={18} /><div className="ripple-result"><small>FINAL OUTCOME</small><b>{pct(preview.simulation.kpis.overflow_probability)}</b><span>modelled overflow risk</span></div></div><div className="ripple-contributions">{preview.ripple.contributions.map(c => <div key={c.cause}><span>{c.cause}</span><ArrowDown size={12} /><b>{c.value > 0 ? '+' : ''}{fmt(c.value, 2)} <small>{c.unit}</small></b><span>{c.effect}</span></div>)}</div></> : <p className="inline-empty">Evaluate an intervention to inspect its direct effect and cross-domain contributions.</p>}
              {!!timeline.length && <><div className="chart-title"><span>Counterfactual trajectory · numerical simulation</span><select aria-label="Chart metric" value={metric} onChange={e => setMetric(e.target.value)}><option value="waste_fill_pct">Bin fill (%)</option><option value="traffic_delay_seconds">Traffic delay (s)</option><option value="energy_demand_kw">Energy demand (kW)</option><option value="reservoir_min_pct">Reservoir (%)</option><option value="pump_kw">Pump demand (kW)</option></select></div><Trajectory baseline={timeline} action={preview?.simulation.series} metric={metric} unit={metric.includes('kw') ? ' kW' : metric.includes('seconds') ? 's' : '%'} /></>}
            </section>

            <section className="panel service-lab"><div className="panel-heading"><div><h2>Service model lab</h2><p>Inspect discrete traffic, water and energy controls in {zone}.</p></div><span className="subtle-tag">WHAT-IF ONLY</span></div><div className="lab-controls"><select aria-label="Domain action" value={labAction} onChange={e => setLabAction(e.target.value)}>{labActions.map(a => <option key={a.id} value={a.id}>{a.label}</option>)}</select><button className="secondary" disabled={!!busy || !labAction} onClick={() => work('Simulating what-if', async () => {
                const action = labActions.find(a => a.id === labAction)!
                const result = await api<Evaluation>('/api/v1/what-if/simulate', { ...request(), action })
                exportJSON(result, `what-if-${action.id}.json`)
                setNotice(`What-if complete: ${result.budget.passed ? 'all constraints pass' : 'constraints failed'}. Numerical result downloaded; no state was changed.`)
              })}>Simulate & export <Download size={13} /></button></div></section>
          </div>

          <div className="right-column">
            <section className="panel outlook"><div className="panel-heading"><div><h2>On the horizon</h2><p>Next 5 min · waste risk 60 min · {zone}</p></div><span className="alert-count">{alerts.filter(a => a.zone_id === zone).length} alerts</span></div>
              <ForecastRow icon={<TrafficCone size={15} />} label="Traffic arrivals" value={`${fmt(predictedZone?.traffic.predicted)} veh/min`} active={!!predictedZone?.alerts.some(a => a.domain === 'traffic')} detail={`${predictedZone?.traffic.method.replace('_', ' ') ?? '—'} forecast`} />
              <ForecastRow icon={<Zap size={15} />} label="Energy demand" value={`${fmt(predictedZone?.energy.predicted, 0)} kW`} active={!!predictedZone?.alerts.some(a => a.domain === 'energy')} detail={`Held-out MAE ${fmt(predictedZone?.energy.validation_mae)} kW`} />
              <ForecastRow icon={<Droplets size={15} />} label="Water consumption" value={`${fmt(selectedZone?.water.demand_m3h, 0)} m³/h`} active={!!predictedZone?.alerts.some(a => a.domain === 'water')} detail={predictedZone && predictedZone.water_anomaly_score > 3 ? 'Abnormal pattern — investigate zone' : 'Within synthetic historical range'} />
              <ForecastRow icon={<Truck size={15} />} label="Waste overflow" value={pct(predictedZone?.waste_overflow_probability)} active={(predictedZone?.waste_overflow_probability ?? 0) >= 0.1} detail="Assumed fill-rate distribution" />
              {(predictedZone?.traffic.low_confidence || predictedZone?.energy.low_confidence || predictedZone?.water.low_confidence) && <p className="forecast-confidence">Low-confidence forecast: large historical residuals. Operator review required.</p>}
              <p className="footnote">Model probabilities are not field calibrated. Forecast residuals are measured on synthetic history.</p>
            </section>

            <section className="panel" id="budget"><div className="panel-heading"><div className="heading-icon"><ShieldCheck size={19} /><div><h2>Impact budget</h2><p>Your limits define safe to act.</p></div></div></div>
              <div className="budget-inputs">{([
                ['traffic_delay_max_delta', 'Traffic delay increase', '%', 0.5], ['energy_demand_max_delta', 'Energy demand increase', '%', 0.5],
                ['water_reservoir_min', 'Reservoir minimum', '%', 5], ['waste_overflow_max', 'Overflow risk target', '%', 1],
                ['cost_max', 'Operating cost limit', '₹', 500], ['emissions_proxy_max', 'Emissions proxy limit', 'kg', 5],
                ['route_duration_max', 'Route duration limit', 'min', 5],
              ] as const).map(([key, label, unit, step]) => <label key={key}><span>{label}</span><div><input aria-label={label} type="number" min={key === 'waste_overflow_max' || key === 'route_duration_max' ? 1 : 0} max={key === 'water_reservoir_min' || key === 'waste_overflow_max' ? 100 : undefined} step={step} value={key === 'waste_overflow_max' ? budget[key] * 100 : budget[key]} onChange={e => { setBudget({ ...budget, [key]: +e.target.value / (key === 'waste_overflow_max' ? 100 : 1) }); clearDecision() }} /><small>{unit}</small></div></label>)}</div>
              <details className="weights"><summary>Soft objective weights</summary>{Object.entries(weights).map(([key, value]) => <label key={key}>{key}<input aria-label={`${key} weight`} type="range" min="0" max="1" step="0.1" value={value} onChange={e => { setWeights({ ...weights, [key]: +e.target.value }); clearDecision() }} /><b>{value.toFixed(1)}</b></label>)}</details>
              {preview && <div className="constraint-results"><div className={`gate ${preview.budget.passed ? 'pass' : 'fail'}`}><ShieldCheck size={17} />SAFE-TO-ACT GATE <b>{preview.budget.passed ? 'PASS' : 'FAIL'}</b></div>{activeConstraints.slice(0, 7).map(c => <div className="constraint-row" key={c.name}><span>{names[c.name]}</span><b>{c.name === 'waste_overflow' ? pct(c.actual) : fmt(c.actual, 2)}<small>{c.name !== 'waste_overflow' ? ` ${c.unit}` : ''}</small></b>{c.status === 'PASS' ? <Check size={14} className="safe-text" /> : <X size={14} className="danger-text" />}</div>)}<details><summary>All physical checks & margins</summary>{activeConstraints.map(c => <p key={c.name}>{c.name}: {c.status} · actual {fmt(c.actual, 3)} / limit {fmt(c.allowed, 3)} · margin {fmt(c.margin, 3)}</p>)}</details></div>}
            </section>

            <section className={`panel passport-panel ${approved ? 'approved' : ''}`} id="passport"><div className="passport-header"><FileCheck2 size={22} /><div><h2>Action Passport</h2><p>A decision you can explain.</p></div><span className="passport-status">{passport?.approval_status ?? 'NOT ISSUED'}</span></div>
              {passport ? <div className="passport-body"><div className="passport-id">{passport.id}<button aria-label="Download Action Passport" onClick={() => exportJSON(passport, `${passport.id}.json`)}><Download size={16} /></button></div><h3>{passport.proposed_intervention.label}</h3><p>{passport.problem}</p>
                <div className="passport-kpis"><div><small>NO ACTION</small><b>{pct(passport.baseline_kpi.overflow_probability)}</b></div><ArrowRight size={19} /><div><small>WITH ACTION</small><b>{pct(passport.predicted_kpi.overflow_probability)}</b></div></div>
                <div className="passport-meta"><span><CheckCircle2 size={14} />All hard constraints passed</span><span><Truck size={14} />{passport.proposed_intervention.vehicles} vehicle · minimum feasible resources</span><span><Leaf size={14} />₹{fmt(passport.predicted_kpi.cost_inr, 0)} estimated cost</span></div>
                <details><summary>Assumptions, uncertainty & provenance</summary><p>{passport.prediction_uncertainty.kind}</p><p>90% fill sensitivity: {passport.prediction_uncertainty.fill_90pct_interval.map(x => fmt(x)).join(' – ')}%</p><p>Source: synthetic · Seed {passport.simulation_seed} · State {passport.input_state_id}</p>{passport.assumptions.map(a => <p key={a}>{a}</p>)}<p>{passport.reversibility}</p><pre>{JSON.stringify(passport.model_versions, null, 2)}</pre></details>
                {isPreviewAlternative && <div className="preview-warning">The map previews an alternative. Approval applies to this minimum-action passport.</div>}
                {passport.approval_status === 'pending' ? <><label className="operator-label">Approving operator<input value={operator} maxLength={100} onChange={e => setOperator(e.target.value)} /></label><label className="operator-label">Decision note (optional)<input value={note} maxLength={1000} onChange={e => setNote(e.target.value)} /></label><div className="approval-actions"><button className="primary" disabled={!!busy || !operator.trim()} onClick={() => decide(true)}><Check size={15} />Approve & simulate</button><button className="reject-button" disabled={!!busy || !operator.trim()} onClick={() => decide(false)}>Reject</button></div><p className="footnote">Approval rechecks state freshness and every hard limit. Simulated execution only.</p></> : <div className={`decision-record ${approved ? 'safe-text' : ''}`}><CheckCircle2 size={18} /><b>{approved ? 'Approved and simulated' : 'Rejected by operator'}</b>{approved && <span>Outcome recorded. Ward state updated.</span>}</div>}
              </div> : <div className="passport-empty"><ShieldCheck size={34} /><p>A passport is issued only after an intervention passes every hard constraint.</p><span>Human approval is always required.</span></div>}
            </section>
            {archive.length > 0 && <details className="panel archive"><summary>Passport archive · {archive.length}</summary>{archive.slice(-10).reverse().map(p => <button key={p.id} onClick={() => exportJSON(p, `${p.id}.json`)}><span>{p.id}<small>{p.approval_status} · seed {p.simulation_seed}</small></span><Download size={14} /></button>)}</details>}
          </div>
        </div>
        <footer><span>URBANNEXUS <b>Prototype 0.1</b></span><span>Zone-level data · No citizen PII · No real actuators</span><a href="/docs" target="_blank" rel="noreferrer">API documentation ↗</a></footer>
      </div>
    </fieldset></main>
    {busy && <div className="busy-indicator" role="status"><Loader2 className="spin" size={16} />{busy}…</div>}
  </div>
}

function Kpi({ icon, title, value, unit, detail, color, footer }: { icon: React.ReactNode; title: string; value: string; unit: string; detail: string; color: string; footer: string }) {
  return <article className={`kpi-card ${color}`}><div className="kpi-title"><span>{title}</span><i>{icon}</i></div><div className="kpi-value">{value}<span>{unit}</span></div><p>{detail}</p><div className="kpi-footer"><span className="tiny-dot" />{footer}</div></article>
}
function ForecastRow({ icon, label, value, active, detail }: { icon: React.ReactNode; label: string; value: string; active: boolean; detail: string }) {
  return <div className={`forecast-row ${active ? 'alert' : ''}`}><div className="forecast-icon">{icon}</div><div><span>{label}</span><p>{detail}</p></div><b>{value}</b>{active && <i />}</div>
}
