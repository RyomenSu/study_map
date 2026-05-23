import { useEffect, useState } from "react";
import { BarChart2, Users, BookOpen, TrendingUp, MapPin } from "lucide-react";
import { api } from "../api/client";
import type { SchoolMetrics } from "../types";

function gradeColor(avg: number | null): string {
  if (avg === null) return "bg-gray-100 text-gray-400";
  if (avg >= 85) return "bg-green-100 text-green-700";
  if (avg >= 70) return "bg-blue-100 text-blue-700";
  if (avg >= 55) return "bg-yellow-100 text-yellow-700";
  return "bg-red-100 text-red-700";
}

function attendanceColor(rate: number | null): string {
  if (rate === null) return "bg-gray-200";
  if (rate >= 90) return "bg-green-500";
  if (rate >= 75) return "bg-blue-500";
  if (rate >= 60) return "bg-yellow-500";
  return "bg-red-500";
}

function regionColor(avg: number | null): string {
  if (avg === null) return "#e5e7eb";
  if (avg >= 85) return "#22c55e";
  if (avg >= 70) return "#3b82f6";
  if (avg >= 55) return "#eab308";
  return "#ef4444";
}

export function AnalyticsPage() {
  const [metrics, setMetrics] = useState<SchoolMetrics[]>([]);
  const [regions, setRegions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      api.get("/analytics/schools").then((r) => setMetrics(r.data)),
      api.get("/analytics/regions").then((r) => setRegions(r.data)),
    ]).finally(() => setLoading(false));
  }, []);

  const regionGroups = metrics.reduce<Record<string, SchoolMetrics[]>>((acc, s) => {
    (acc[s.region] = acc[s.region] || []).push(s);
    return acc;
  }, {});

  if (loading) return <div className="text-center py-20 text-gray-400">Loading analytics...</div>;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Regional Analytics</h1>
        <p className="text-gray-500 mt-1">School performance comparison across regions</p>
      </div>

      {/* Region summary pills */}
      {regions.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-gray-800 mb-3">Regions at a glance</h2>
          <div className="flex flex-wrap gap-3">
            {regions.map((r) => (
              <div
                key={r.region}
                className="flex items-center gap-2 px-4 py-2 rounded-full text-white text-sm font-medium shadow-sm"
                style={{ backgroundColor: regionColor(r.avg_grade) }}
              >
                <MapPin className="w-4 h-4" />
                {r.region}
                {r.avg_grade != null && <span className="opacity-80">— {r.avg_grade}%</span>}
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Colors: green ≥85% · blue ≥70% · yellow ≥55% · red &lt;55%
          </p>
        </div>
      )}

      {/* Per-region breakdown */}
      {Object.entries(regionGroups).map(([region, schools]) => {
        const avgGrades = schools.filter((s) => s.avg_grade != null).map((s) => s.avg_grade!);
        const regionAvg = avgGrades.length ? Math.round(avgGrades.reduce((a, b) => a + b, 0) / avgGrades.length) : null;

        return (
          <div key={region}>
            <div className="flex items-center gap-3 mb-4">
              <div
                className="w-4 h-4 rounded-full flex-shrink-0"
                style={{ backgroundColor: regionColor(regionAvg) }}
              />
              <h2 className="text-lg font-semibold text-gray-900">{region}</h2>
              {regionAvg != null && (
                <span className="text-sm text-gray-500">avg grade: {regionAvg}%</span>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {schools.map((school) => (
                <div key={school.school_id} className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h3 className="font-semibold text-gray-900">{school.school_name}</h3>
                      <p className="text-sm text-gray-500">{school.city}</p>
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full font-semibold ${gradeColor(school.avg_grade)}`}>
                      {school.avg_grade != null ? `${school.avg_grade}%` : "N/A"}
                    </span>
                  </div>

                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between text-gray-600">
                      <span className="flex items-center gap-1.5"><Users className="w-3.5 h-3.5" /> Students</span>
                      <span className="font-medium">{school.total_students}</span>
                    </div>
                    <div className="flex items-center justify-between text-gray-600">
                      <span className="flex items-center gap-1.5"><BookOpen className="w-3.5 h-3.5" /> Courses</span>
                      <span className="font-medium">{school.total_courses}</span>
                    </div>
                    {school.attendance_rate != null && (
                      <div>
                        <div className="flex items-center justify-between text-gray-600 mb-1">
                          <span className="flex items-center gap-1.5"><TrendingUp className="w-3.5 h-3.5" /> Attendance</span>
                          <span className="font-medium">{school.attendance_rate}%</span>
                        </div>
                        <div className="bg-gray-100 rounded-full h-1.5 overflow-hidden">
                          <div
                            className={`h-full rounded-full ${attendanceColor(school.attendance_rate)}`}
                            style={{ width: `${school.attendance_rate}%` }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}

      {metrics.length === 0 && (
        <div className="text-center py-16 text-gray-400">
          No school data yet. Create schools via the API and assign users to them.
        </div>
      )}
    </div>
  );
}
