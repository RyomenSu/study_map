import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, CheckCircle, FileText, TrendingUp } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import { useAuth } from "../store/auth";
import type { Course, Assignment } from "../types";

export function Dashboard() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [recentAssignments, setRecentAssignments] = useState<Assignment[]>([]);

  useEffect(() => {
    api.get("/courses")
      .then((r) => {
        setCourses(r.data);
        r.data.slice(0, 3).forEach((c: Course) => {
          api.get(`/courses/${c.id}/assignments`).then((ar) => {
            setRecentAssignments((prev) => [...prev, ...ar.data.slice(0, 2)]);
          });
        });
      })
      .catch(() => toast.error("Failed to load courses"));
  }, []);

  const stats = [
    { label: "Courses", value: courses.length, icon: BookOpen, color: "bg-blue-50 text-blue-600" },
    { label: "Assignments", value: recentAssignments.length, icon: FileText, color: "bg-purple-50 text-purple-600" },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Welcome back, {user?.full_name?.split(" ")[0]}</h1>
        <p className="text-gray-500 mt-1">Here's what's happening in your portal</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4">
            <div className={`p-3 rounded-lg ${color}`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{value}</p>
              <p className="text-sm text-gray-500">{label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Courses */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900">My Courses</h2>
          <Link to="/courses" className="text-sm text-brand-600 hover:underline">View all</Link>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {courses.slice(0, 6).map((course) => (
            <Link
              key={course.id}
              to={`/courses/${course.id}`}
              className="bg-white rounded-xl border border-gray-200 p-5 hover:border-brand-300 hover:shadow-md transition-all group"
            >
              <div className="flex items-start justify-between">
                <div className="p-2 bg-brand-50 rounded-lg group-hover:bg-brand-100 transition-colors">
                  <BookOpen className="w-5 h-5 text-brand-600" />
                </div>
              </div>
              <h3 className="font-semibold text-gray-900 mt-3">{course.name}</h3>
              {course.description && (
                <p className="text-sm text-gray-500 mt-1 line-clamp-2">{course.description}</p>
              )}
            </Link>
          ))}
          {courses.length === 0 && (
            <div className="col-span-3 text-center py-12 text-gray-400">
              No courses yet. {user?.role !== "student" && (
                <Link to="/courses" className="text-brand-600 hover:underline">Create one</Link>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Recent assignments */}
      {recentAssignments.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Assignments</h2>
          <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
            {recentAssignments.slice(0, 5).map((a) => (
              <div key={a.id} className="px-5 py-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FileText className="w-4 h-4 text-gray-400" />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{a.title}</p>
                    {a.due_date && (
                      <p className="text-xs text-gray-400">
                        Due {new Date(a.due_date).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
                <span className="text-xs text-gray-500">{a.max_score} pts</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
