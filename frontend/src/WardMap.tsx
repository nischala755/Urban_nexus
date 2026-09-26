import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import type { Road, Zone } from './types'

export default function WardMap({ zones, roads, route, selected, onSelect }: {
  zones: Zone[]; roads: Road[]; route: string[]; selected: string; onSelect: (id: string) => void
}) {
  const element = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  useEffect(() => {
    if (!element.current) return
    const instance = L.map(element.current, { crs: L.CRS.Simple, minZoom: 0, maxZoom: 4, zoomSnap: 0.1, zoomControl: false,
      attributionControl: false, scrollWheelZoom: false, dragging: true })
    map.current = instance
    instance.fitBounds([[12, -10], [89, 106]], { padding: [18, 28] })
    L.control.zoom({ position: 'bottomright' }).addTo(instance)
    const observer = new ResizeObserver(() => instance.invalidateSize())
    observer.observe(element.current)
    return () => { observer.disconnect(); instance.remove(); map.current = null }
  }, [])
  useEffect(() => {
    const instance = map.current
    if (!instance) return
    const layer = L.layerGroup().addTo(instance)
    const points: Record<string, L.LatLngTuple> = { DEPOT: [45, 8] }
    zones.forEach(z => { points[z.id] = [z.y, z.x] })
    // Local schematic. All service values and highlighted routes come from the API.
    L.polyline([[0, 88], [24, 90], [45, 96], [72, 88], [100, 91]], { color: '#bddde0', weight: 24, opacity: 0.7 }).addTo(layer)
    for (const road of roads) {
      if (!points[road.a] || !points[road.b]) continue
      L.polyline([points[road.a], points[road.b]], { color: '#d1d8d2', weight: 11 }).addTo(layer)
      L.polyline([points[road.a], points[road.b]], { color: '#ffffff', weight: 6 }).addTo(layer)
      const label = `${road.km} km · ${road.capacity_vpm} veh/min synthetic capacity`
      L.polyline([points[road.a], points[road.b]], { color: '#a8b9ae', weight: 1, dashArray: '3 6' }).bindTooltip(label).addTo(layer)
    }
    if (route.length > 1) L.polyline(route.map(id => points[id]).filter(Boolean), { color: '#14796f', weight: 5, dashArray: '9 7' }).addTo(layer)
    for (const z of zones) {
      const selectedZone = z.id === selected
      const node = document.createElement('div')
      node.className = `map-node ${selectedZone ? 'chosen' : ''} ${z.waste.fill_pct > 75 ? 'warning' : ''}`
      const id = document.createElement('b'); id.textContent = z.id
      const fill = document.createElement('span'); fill.textContent = `${z.waste.fill_pct.toFixed(0)}% fill`
      const name = document.createElement('small'); name.textContent = z.name
      node.append(id, fill, name)
      const width = (element.current?.clientWidth ?? 800) < 500 ? 91 : 126
      const marker = L.marker([z.y, z.x], { icon: L.divIcon({ className: 'zone-marker', iconSize: [width, 75], iconAnchor: [width / 2, 37], html: node }) })
      marker.on('click', () => onSelect(z.id)).addTo(layer)
    }
    L.marker([45, 8], { icon: L.divIcon({ className: 'depot-marker', html: '<span>▦</span><b>DEPOT</b>', iconSize: [60, 50], iconAnchor: [30, 25] }) }).addTo(layer)
    return () => { layer.remove() }
  }, [zones, roads, route, selected, onSelect])
  return <div ref={element} className="ward-map" aria-label="Synthetic ward map with zones and candidate collection route" />
}
