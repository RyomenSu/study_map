import { useState } from 'react'
import { getSchoolStats } from '../api'

interface SubjectStat {
  subject: string
  avg_score: number
  at_risk: number
  student_count: number
}

export default function SchoolView() {
  const [schoolId, setSchoolId] = useState('')
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    const id = parseInt(schoolId)
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const d = await getSchoolStats(id)
      setData(d)
    } catch {
      setError('Школа не найдена')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-4">
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex gap-3 items-center">
        <input
          type="number"
          placeholder="ID школы (например: 1)"
          value={schoolId}
          onChange={(e) => setSchoolId(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && load()}
          className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm outline-none focus:border-blue-500"
        />
        <button
          onClick={load}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 px-5 py-2 rounded text-sm font-medium transition-colors"
        >
          {loading ? 'Загрузка...' : 'Показать'}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {data && (
        <>
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h2 className="font-bold text-lg">{data.school.name}</h2>
            <p className="text-gray-400 text-sm">ID региона: {data.school.region_id}</p>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
            <h3 className="font-semibold mb-3">Успеваемость по предметам</h3>
            <div className="flex flex-col gap-3">
              {data.subject_stats.map((s: SubjectStat) => (
                <div key={s.subject}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="font-medium">{s.subject}</span>
                    <span className="flex gap-4 text-gray-400">
                      <span className="text-red-400">{s.at_risk} в риске</span>
                      <span>{s.student_count} учеников</span>
                      <span className={s.avg_score >= 70 ? 'text-green-400' : s.avg_score >= 50 ? 'text-yellow-400' : 'text-red-400'}>
                        {s.avg_score} балл
                      </span>
                    </span>
                  </div>
                  <div className="bg-gray-800 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${s.avg_score >= 70 ? 'bg-green-500' : s.avg_score >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`}
                      style={{ width: `${s.avg_score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {data.recommendations.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h3 className="font-semibold mb-3 text-blue-300">🤖 AI рекомендации для школы</h3>
              {data.recommendations.map((rec: any, i: number) => (
                <div key={i} className="flex flex-col gap-1 mb-3">
                  {(rec.actions || []).map((a: string, j: number) => (
                    <div key={j} className="bg-blue-950/50 border border-blue-900 rounded p-2 text-sm text-blue-200">
                      {j + 1}. {a}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
