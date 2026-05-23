import { useEffect, useState } from 'react'
import { getNationalStats, getNationalRecommendations, getAlerts } from '../api'
import UzbekistanMap from '../components/UzbekistanMap'

interface Region {
  id: number
  name: string
  avg_score: number
  at_risk_count: number
  student_count: number
  trend: number
  anomaly?: boolean
}

function ScoreBadge({ score }: { score: number }) {
  const cls =
    score >= 70 ? 'bg-green-900 text-green-300' :
    score >= 50 ? 'bg-yellow-900 text-yellow-300' :
                  'bg-red-900 text-red-300'
  return <span className={`px-2 py-0.5 rounded text-xs font-bold ${cls}`}>{score}</span>
}

function TrendBadge({ trend }: { trend: number }) {
  const up = trend > 0
  return (
    <span className={`text-xs font-medium ${up ? 'text-green-400' : 'text-red-400'}`}>
      {up ? '▲' : '▼'} {Math.abs(trend).toFixed(1)}
    </span>
  )
}

export default function NationalView() {
  const [regions, setRegions] = useState<Region[]>([])
  const [selected, setSelected] = useState<Region | null>(null)
  const [recs, setRecs] = useState<any[]>([])
  const [alerts, setAlerts] = useState<any[]>([])

  useEffect(() => {
    getNationalStats().then((d) => setRegions(d.regions))
    getNationalRecommendations().then((d) => setRecs(d.recommendations))
    getAlerts().then((d) => setAlerts(d.alerts))
  }, [])

  const selectedRec = recs.find((r) => r.region === selected?.name)

  return (
    <div className="flex flex-col gap-4">
      {alerts.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          {alerts.map((a, i) => (
            <div key={i} className="bg-orange-900/40 border border-orange-700 rounded px-3 py-1.5 text-sm flex items-center gap-2">
              <span>⚠️</span>
              {a.type === 'region_spike'
                ? `${a.region}: резкий рост +${a.change_pct}% (${a.prev_avg} → ${a.recent_avg})`
                : a.type === 'student_sudden_jump'
                ? `Ученик ${a.student_id}: прыжок ${a.from} → ${a.to} по ${a.subject}`
                : `Аномалия: ${a.type}`}
            </div>
          ))}
        </div>
      )}

      <div className="flex gap-4" style={{ height: '460px' }}>
        <div className="flex-1 rounded-lg overflow-hidden border border-gray-800">
          <UzbekistanMap regions={regions} selected={selected} onSelect={setSelected} />
        </div>

        <div className="w-80 flex flex-col gap-3">
          {selected ? (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h2 className="font-bold text-lg">{selected.name}</h2>
                <button onClick={() => setSelected(null)} className="text-gray-500 hover:text-white text-lg">✕</button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <Stat label="Средний балл" value={<ScoreBadge score={selected.avg_score} />} />
                <Stat label="Тренд" value={<TrendBadge trend={selected.trend} />} />
                <Stat label="В зоне риска" value={<span className="text-red-400 font-bold">{selected.at_risk_count}</span>} />
                <Stat label="Учеников" value={<span className="text-blue-400 font-bold">{selected.student_count}</span>} />
              </div>
              {selectedRec && (
                <div>
                  <p className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">AI рекомендации</p>
                  <div className="flex flex-col gap-2">
                    {selectedRec.actions.map((a: string, i: number) => (
                      <div key={i} className="bg-blue-950/50 border border-blue-900 rounded p-2 text-xs text-blue-200">
                        {i + 1}. {a}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <p className="text-gray-400 text-sm">Нажмите на регион на карте для детального просмотра</p>
              <div className="flex gap-3 mt-3 text-xs">
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-green-500 inline-block" /> ≥70</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-yellow-500 inline-block" /> 50–70</span>
                <span className="flex items-center gap-1"><span className="w-3 h-3 rounded-full bg-red-500 inline-block" /> &lt;50</span>
              </div>
            </div>
          )}

          <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 flex-1 overflow-y-auto">
            <p className="text-xs text-gray-400 mb-2 font-semibold uppercase tracking-wide">Все регионы</p>
            <div className="flex flex-col gap-1">
              {[...regions].sort((a, b) => b.avg_score - a.avg_score).map((r) => (
                <button
                  key={r.id}
                  onClick={() => setSelected(r)}
                  className={`flex items-center justify-between px-2 py-1.5 rounded text-sm text-left transition-colors ${
                    selected?.id === r.id ? 'bg-blue-900/50' : 'hover:bg-gray-800'
                  }`}
                >
                  <span className="text-gray-200 truncate">{r.name}</span>
                  <div className="flex items-center gap-2 shrink-0">
                    <TrendBadge trend={r.trend} />
                    <ScoreBadge score={r.avg_score} />
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {recs.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="font-semibold mb-3 text-blue-300">🤖 AI рекомендации для Министерства</h3>
          <div className="grid grid-cols-2 gap-3">
            {recs.slice(0, 4).map((rec, i) => (
              <div key={i} className="bg-gray-800 rounded-lg p-3">
                <p className="text-sm font-semibold text-gray-200 mb-2">{rec.region}</p>
                <div className="flex flex-col gap-1">
                  {(rec.actions || []).slice(0, 2).map((a: string, j: number) => (
                    <p key={j} className="text-xs text-gray-400">• {a}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-gray-800 rounded p-2">
      <p className="text-xs text-gray-500">{label}</p>
      <div className="mt-0.5">{value}</div>
    </div>
  )
}
