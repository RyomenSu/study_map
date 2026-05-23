import { useEffect, useState } from "react";
import { CheckCircle, XCircle, Clock, AlertCircle, Plus, X } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import { useAuth } from "../store/auth";
import type { Course, AttendanceSession, AttendanceStatus } from "../types";

const statusColors: Record<AttendanceStatus, string> = {
  present: "bg-green-100 text-green-700",
  absent: "bg-red-100 text-red-700",
  late: "bg-yellow-100 text-yellow-700",
  excused: "bg-gray-100 text-gray-600",
};

const statusIcons: Record<AttendanceStatus, React.ElementType> = {
  present: CheckCircle,
  absent: XCircle,
  late: Clock,
  excused: AlertCircle,
};

export function AttendancePage() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>("");
  const [sessions, setSessions] = useState<AttendanceSession[]>([]);
  const [students, setStudents] = useState<{ id: string; full_name: string }[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [sessionDate, setSessionDate] = useState(new Date().toISOString().split("T")[0]);
  const [records, setRecords] = useState<Record<string, AttendanceStatus>>({});
  const [summary, setSummary] = useState<any[]>([]);

  const isTeacherOrAdmin = user?.role === "teacher" || user?.role === "admin";

  useEffect(() => {
    api.get("/courses").then((r) => {
      setCourses(r.data);
      if (r.data.length > 0) setSelectedCourse(r.data[0].id);
    });
  }, []);

  useEffect(() => {
    if (!selectedCourse) return;
    api.get(`/courses/${selectedCourse}/attendance`).then((r) => setSessions(r.data));
    api.get(`/courses/${selectedCourse}/attendance/summary`).then((r) => setSummary(r.data));
    if (isTeacherOrAdmin) {
      api.get(`/courses/${selectedCourse}/students`).then((r) => {
        setStudents(r.data);
        const init: Record<string, AttendanceStatus> = {};
        r.data.forEach((s: any) => { init[s.id] = "present"; });
        setRecords(init);
      });
    }
  }, [selectedCourse]);

  const submitSession = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post(`/courses/${selectedCourse}/attendance`, {
        session_date: sessionDate,
        records: Object.entries(records).map(([student_id, status]) => ({ student_id, status })),
      });
      toast.success("Attendance recorded!");
      setShowCreate(false);
      api.get(`/courses/${selectedCourse}/attendance`).then((r) => setSessions(r.data));
      api.get(`/courses/${selectedCourse}/attendance/summary`).then((r) => setSummary(r.data));
    } catch {
      toast.error("Failed to record attendance");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Attendance</h1>
        {isTeacherOrAdmin && selectedCourse && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700"
          >
            <Plus className="w-4 h-4" /> Mark attendance
          </button>
        )}
      </div>

      {/* Course selector */}
      <select
        value={selectedCourse}
        onChange={(e) => setSelectedCourse(e.target.value)}
        className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
      >
        {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
      </select>

      {/* Summary cards */}
      {summary.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-3">Attendance Summary</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {summary.map((s) => (
              <div key={s.student_id} className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-xs text-gray-400 font-mono">{s.student_id.slice(0, 8)}</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-2xl font-bold text-gray-900">{s.attendance_rate}%</span>
                  <div className="text-right text-xs text-gray-500">
                    <p>{s.present}P / {s.absent}A / {s.late}L</p>
                    <p>{s.total_sessions} sessions</p>
                  </div>
                </div>
                <div className="mt-2 bg-gray-100 rounded-full h-1.5 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${s.attendance_rate >= 80 ? "bg-green-500" : s.attendance_rate >= 60 ? "bg-yellow-500" : "bg-red-500"}`}
                    style={{ width: `${s.attendance_rate}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Sessions list */}
      <div>
        <h2 className="text-base font-semibold text-gray-800 mb-3">Sessions</h2>
        <div className="space-y-3">
          {sessions.map((session) => (
            <div key={session.id} className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm font-semibold text-gray-800 mb-3">
                {new Date(session.session_date).toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" })}
              </p>
              <div className="flex flex-wrap gap-2">
                {session.records.map((rec) => {
                  const Icon = statusIcons[rec.status];
                  return (
                    <span key={rec.id} className={`flex items-center gap-1 text-xs px-2.5 py-1 rounded-full font-medium ${statusColors[rec.status]}`}>
                      <Icon className="w-3 h-3" />
                      {rec.student_id.slice(0, 6)} — {rec.status}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="text-center py-10 text-gray-400">No attendance sessions yet.</div>
          )}
        </div>
      </div>

      {/* Mark attendance modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Mark Attendance</h2>
              <button onClick={() => setShowCreate(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <form onSubmit={submitSession} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                <input
                  type="date"
                  value={sessionDate}
                  onChange={(e) => setSessionDate(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div className="space-y-2">
                {students.map((s) => (
                  <div key={s.id} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <span className="text-sm font-medium text-gray-800">{s.full_name}</span>
                    <select
                      value={records[s.id] || "present"}
                      onChange={(e) => setRecords((r) => ({ ...r, [s.id]: e.target.value as AttendanceStatus }))}
                      className="px-2 py-1 border border-gray-300 rounded text-sm focus:outline-none"
                    >
                      <option value="present">Present</option>
                      <option value="absent">Absent</option>
                      <option value="late">Late</option>
                      <option value="excused">Excused</option>
                    </select>
                  </div>
                ))}
                {students.length === 0 && (
                  <p className="text-sm text-gray-400 text-center py-4">No enrolled students found.</p>
                )}
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button type="submit" className="flex-1 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700">Save attendance</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
