import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet'

const REGION_COORDS: Record<string, [number, number]> = {
  'Ташкент':             [41.2995, 69.2401],
  'Ташкентская область': [41.10,   69.85],
  'Самарканд':           [39.6542, 66.9597],
  'Бухара':              [39.7747, 64.4286],
  'Фергана':             [40.3864, 71.7864],
  'Андижан':             [40.7821, 72.3442],
  'Наманган':            [41.0011, 71.6714],
  'Кашкадарья':          [38.8671, 65.7903],
  'Сурхандарья':         [37.9401, 67.5703],
  'Навои':               [40.0904, 65.3842],
  'Хорезм':              [41.3689, 60.3608],
  'Джизак':              [40.1158, 67.8422],
  'Сырдарья':            [40.8383, 68.6608],
  'Каракалпакстан':      [43.7353, 59.5757],
}

interface Region {
  id: number
  name: string
  avg_score: number
  at_risk_count: number
  student_count: number
  trend: number
}

interface Props {
  regions: Region[]
  selected: Region | null
  onSelect: (r: Region) => void
}

function scoreColor(score: number): string {
  if (score >= 70) return '#22c55e'
  if (score >= 50) return '#eab308'
  return '#ef4444'
}

export default function UzbekistanMap({ regions, selected, onSelect }: Props) {
  return (
    <MapContainer
      center={[41.0, 64.5]}
      zoom={5}
      style={{ height: '100%', width: '100%', background: '#0f172a' }}
      className="rounded-lg"
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution="&copy; OpenStreetMap &copy; CARTO"
      />
      {regions.map((region) => {
        const coords = REGION_COORDS[region.name]
        if (!coords) return null
        const isSelected = selected?.id === region.id
        return (
          <CircleMarker
            key={region.id}
            center={coords}
            radius={isSelected ? 22 : 16}
            pathOptions={{
              fillColor: scoreColor(region.avg_score),
              fillOpacity: 0.85,
              color: isSelected ? '#fff' : '#00000044',
              weight: isSelected ? 2.5 : 1,
            }}
            eventHandlers={{ click: () => onSelect(region) }}
          >
            <Tooltip direction="top" offset={[0, -10]} permanent={false}>
              <div className="text-xs font-semibold">
                <div>{region.name}</div>
                <div>Балл: {region.avg_score}</div>
                <div>Риск: {region.at_risk_count} чел.</div>
              </div>
            </Tooltip>
          </CircleMarker>
        )
      })}
    </MapContainer>
  )
}
