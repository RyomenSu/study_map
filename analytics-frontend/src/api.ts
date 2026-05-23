import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

const MOCK_REGIONS = [
  { id: 1,  name: 'Ташкент',              avg_score: 81, at_risk_count: 12, student_count: 420, trend: 3.2,  anomaly: false },
  { id: 2,  name: 'Ташкентская область',  avg_score: 68, at_risk_count: 45, student_count: 380, trend: 1.5,  anomaly: false },
  { id: 3,  name: 'Самарканд',            avg_score: 72, at_risk_count: 38, student_count: 350, trend: 2.1,  anomaly: false },
  { id: 4,  name: 'Бухара',              avg_score: 65, at_risk_count: 52, student_count: 290, trend: -1.0, anomaly: false },
  { id: 5,  name: 'Фергана',             avg_score: 70, at_risk_count: 41, student_count: 400, trend: 0.8,  anomaly: false },
  { id: 6,  name: 'Андижан',             avg_score: 67, at_risk_count: 48, student_count: 360, trend: 1.2,  anomaly: false },
  { id: 7,  name: 'Наманган',            avg_score: 63, at_risk_count: 61, student_count: 310, trend: -0.5, anomaly: false },
  { id: 8,  name: 'Кашкадарья',          avg_score: 58, at_risk_count: 78, student_count: 270, trend: -2.1, anomaly: false },
  { id: 9,  name: 'Сурхандарья',         avg_score: 48, at_risk_count: 95, student_count: 240, trend: -3.5, anomaly: false },
  { id: 10, name: 'Навои',              avg_score: 71, at_risk_count: 35, student_count: 200, trend: 1.8,  anomaly: false },
  { id: 11, name: 'Хорезм',             avg_score: 61, at_risk_count: 67, student_count: 260, trend: -0.8, anomaly: false },
  { id: 12, name: 'Джизак',             avg_score: 69, at_risk_count: 43, student_count: 220, trend: 2.0,  anomaly: false },
  { id: 13, name: 'Сырдарья',           avg_score: 64, at_risk_count: 54, student_count: 180, trend: 0.4,  anomaly: false },
  { id: 14, name: 'Каракалпакстан',     avg_score: 55, at_risk_count: 83, student_count: 300, trend: -1.5, anomaly: false },
]

const MOCK_RECOMMENDATIONS = [
  { region: 'Сурхандарья', actions: ['Направить 10 методистов по математике в районные школы → прогноз +12 баллов за 30 дней', 'Организовать онлайн-марафон по слабым темам с охватом 500+ учеников → прогноз +8 баллов', 'Ввести еженедельный мониторинг домашних заданий для учителей → снижение риска провала на 20%'], created_at: new Date().toISOString() },
  { region: 'Кашкадарья', actions: ['Провести тренинг для учителей по интерактивным методам обучения → прогноз +7 баллов', 'Обеспечить учебниками нового поколения 15 школ → прогноз +5 баллов', 'Запустить программу наставничества: сильные ученики помогают слабым → прогноз +6 баллов'], created_at: new Date().toISOString() },
]

const MOCK_ALERTS = [
  { type: 'region_spike', region: 'Навои', recent_avg: 71, prev_avg: 54, change_pct: 31.5 },
]

export async function getNationalStats() {
  try {
    const { data } = await api.get('/national/stats')
    return data
  } catch {
    return { regions: MOCK_REGIONS, total_regions: 14 }
  }
}

export async function getNationalRecommendations() {
  try {
    const { data } = await api.get('/national/recommendations')
    return data
  } catch {
    return { recommendations: MOCK_RECOMMENDATIONS }
  }
}

export async function getAlerts() {
  try {
    const { data } = await api.get('/alerts')
    return data
  } catch {
    return { alerts: MOCK_ALERTS, count: MOCK_ALERTS.length }
  }
}

export async function getStudentDashboard(studentId: number) {
  const { data } = await api.get(`/student/${studentId}/dashboard`)
  return data
}

export async function getSchoolStats(schoolId: number) {
  const { data } = await api.get(`/school/${schoolId}/stats`)
  return data
}
