import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { BookOpen, Plus, X } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import { useAuth } from "../store/auth";
import type { Course } from "../types";

export function CoursesPage() {
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ name: "", description: "" });
  const [loading, setLoading] = useState(false);

  const fetchCourses = () =>
    api.get("/courses")
      .then((r) => setCourses(r.data))
      .catch(() => toast.error("Failed to load courses"));

  useEffect(() => { fetchCourses(); }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/courses", form);
      toast.success("Course created!");
      setShowCreate(false);
      setForm({ name: "", description: "" });
      fetchCourses();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Failed to create course");
    } finally {
      setLoading(false);
    }
  };

  const canCreate = user?.role === "teacher" || user?.role === "admin";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Courses</h1>
        {canCreate && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700"
          >
            <Plus className="w-4 h-4" /> New course
          </button>
        )}
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Course</h2>
              <button onClick={() => setShowCreate(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <form onSubmit={create} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Course name</label>
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm((f) => ({ ...f, description: e.target.value }))}
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50">
                  Cancel
                </button>
                <button type="submit" disabled={loading} className="flex-1 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700 disabled:opacity-60">
                  {loading ? "Creating..." : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {courses.map((course) => (
          <Link
            key={course.id}
            to={`/courses/${course.id}`}
            className="bg-white rounded-xl border border-gray-200 p-5 hover:border-brand-300 hover:shadow-md transition-all group"
          >
            <div className="p-2 bg-brand-50 rounded-lg w-fit group-hover:bg-brand-100 transition-colors mb-3">
              <BookOpen className="w-5 h-5 text-brand-600" />
            </div>
            <h3 className="font-semibold text-gray-900">{course.name}</h3>
            {course.description && (
              <p className="text-sm text-gray-500 mt-1 line-clamp-3">{course.description}</p>
            )}
            <p className="text-xs text-gray-400 mt-3">
              Created {new Date(course.created_at).toLocaleDateString()}
            </p>
          </Link>
        ))}
        {courses.length === 0 && (
          <div className="col-span-3 text-center py-16 text-gray-400">
            No courses found.
          </div>
        )}
      </div>
    </div>
  );
}
