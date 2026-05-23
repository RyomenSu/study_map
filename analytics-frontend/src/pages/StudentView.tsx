import { useState } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { getStudentDashboard } from '../api'

const SUBJECT_COLORS: Record<string, string> = {
  'математика': '#60a5fa',
  'физика': '#a78bfa',
  'химия': '#34d399',
  'история': '#fb923c',
}

function colorFor(subject: string): string {
  return SUBJECT_COLORS[subject.toLowerCase()] ?? '#94a3b8'
}

export default function StudentView() {
  const [studentId, setStudentId] = useState('')
  const [data, setData] = useState<any>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function load() {
    const id = parseInt(studentId)
    if (!id) return
    setLoading(true)
    setError('')
    try {
      const d = await getStudentDashboard(id)
      setData(d)
    } catch {
      setError('Ученик не найден')
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  const chartData = data
    ? Object.entries(data.progress as Record<string, any[]>)
        .flatMap(([subject, entries]) =>
          entries.map((e: any) => ({ subject, date: e.date.slice(0, 10), score: e.score }))
        )
        .reduce((acc: any[], cur) => {
          const existing = acc.find((a) => a.date === cur.date)
          if (existing) { existing[cur.subject] = cur.score } else { acc.push({ date: cur.date, [cur.subject]: cur.score }) }
          return acc
        }, [])
        .sort((a, b) => a.date.localeCompare(b.date))
    : []

  const subjects = data ? Object.keys(data.progress) : []

  return (
    <div className="max-w-4xl mx-auto flex flex-col gap-4">
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex gap-3 items-center">
        <input
          type="number"
          placeholder="ID ученика (например: 1)"
          value={studentId}
          onChange={(e) => setStudentId(e.target.value)}
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
          <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-between">
            <div>
              <h2 className="font-bold text-lg">{data.student.name}</h2>
              <p className="text-gray-400 text-sm">{data.student.grade} класс</p>
            </div>
          </div>

          {data.predictions.length > 0 && (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {data.predictions.map((p: any) => {
                const pct = Math.round(p.exam_pass_probability)
                const color = pct >= 70 ? 'green' : pct >= 50 ? 'yellow' : 'red'
                return (
                  <div key={p.subject} className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-center">
                    <p className="text-xs text-gray-400 mb-1">{p.subject}</p>
                    <p className={`text-2xl font-bold ${color === 'green' ? 'text-green-400' : color === 'yellow' ? 'text-yellow-400' : 'text-red-400'}`}>
                      {pct}%
                    </p>
                    <p className="text-xs text-gray-500">шанс сдать экзамен</p>
                  </div>
                )
              })}
            </div>
          )}

          {chartData.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h3 className="font-semibold mb-4">Прогресс по предметам</h3>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#6b7280' }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: '#6b7280' }} />
                  <Tooltip contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 6 }} />
                  <Legend />
                  {subjects.map((s) => (
                    <Line key={s} type="monotone" dataKey={s} stroke={colorFor(s)} strokeWidth={2} dot={{ r: 3 }} connectNulls />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {data.roadmap.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
              <h3 className="font-semibold mb-3">📋 Roadmap на неделю</h3>
              <div className="flex flex-col gap-2">
                {data.roadmap.map((item: any, i: number) => (
                  <div key={i} className="flex items-center gap-3 bg-gray-800 rounded p-3">
                    <span className="text-blue-400 font-bold text-sm w-5">{i + 1}</span>
                    <div className="flex-1">
                      <p className="text-sm font-medium">{item.topic}</p>
                      <p className="text-xs text-gray-400">Встречается {item.frequency} раз в слабых темах</p>
                    </div>
                    <span className="text-green-400 text-xs font-medium">+{Math.round(item.frequency * 2.5)} балл</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
