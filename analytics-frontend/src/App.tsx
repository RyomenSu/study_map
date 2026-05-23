import { useState } from 'react'
import NationalView from './pages/NationalView'
import SchoolView from './pages/SchoolView'
import StudentView from './pages/StudentView'

type Tab = 'national' | 'school' | 'student'

export default function App() {
  const [tab, setTab] = useState<Tab>('national')

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-blue-400 text-xl">🎓</span>
          <span className="font-bold text-white">EduAnalytics</span>
          <span className="text-gray-500 text-sm">Министерство образования Узбекистана</span>
        </div>
        <nav className="flex gap-1 ml-auto">
          {(['national', 'school', 'student'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                tab === t
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              }`}
            >
              {t === 'national' ? '🗺 Государство' : t === 'school' ? '🏫 Школа' : '👤 Ученик'}
            </button>
          ))}
        </nav>
      </header>

      <main className="p-4">
        {tab === 'national' && <NationalView />}
        {tab === 'school' && <SchoolView />}
        {tab === 'student' && <StudentView />}
      </main>
    </div>
  )
}
