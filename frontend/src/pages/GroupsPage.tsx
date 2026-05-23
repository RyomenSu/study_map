import { useEffect, useState } from "react";
import { Users, Plus, X, UserPlus, BookOpen, ChevronDown, ChevronRight } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import { useAuth } from "../store/auth";

interface Group { id: string; name: string; school_id: string | null }
interface Student { id: string; full_name: string; email: string; group_id: string | null }
interface Course { id: string; name: string }

export function GroupsPage() {
  const { user } = useAuth();
  const [groups, setGroups] = useState<Group[]>([]);
  const [allStudents, setAllStudents] = useState<Student[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [members, setMembers] = useState<Record<string, Student[]>>({});
  const [courses, setCourses] = useState<Course[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [selectedStudent, setSelectedStudent] = useState<Record<string, string>>({});
  const [assignCourse, setAssignCourse] = useState<Record<string, string>>({});

  const isTeacherOrAdmin = user?.role === "teacher" || user?.role === "admin";

  const fetchGroups = () => api.get("/groups").then((r) => setGroups(r.data));
  const fetchStudents = () => api.get("/users?role=student").then((r) => setAllStudents(r.data));

  useEffect(() => {
    fetchGroups();
    api.get("/courses").then((r) => setCourses(r.data));
    if (isTeacherOrAdmin) fetchStudents();
  }, []);

  const fetchMembers = async (groupId: string) => {
    const r = await api.get(`/groups/${groupId}/members`);
    setMembers((m) => ({ ...m, [groupId]: r.data }));
  };

  const toggleExpand = async (groupId: string) => {
    if (expanded === groupId) { setExpanded(null); return; }
    setExpanded(groupId);
    await fetchMembers(groupId);
  };

  const createGroup = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post("/groups", { name: newName });
      toast.success("Group created!");
      setShowCreate(false);
      setNewName("");
      fetchGroups();
    } catch { toast.error("Failed to create group"); }
  };

  const addStudent = async (groupId: string) => {
    const studentId = selectedStudent[groupId];
    if (!studentId) return;
    try {
      await api.post(`/groups/${groupId}/members`, { student_id: studentId });
      toast.success("Student added!");
      await fetchMembers(groupId);
      await fetchStudents(); // refresh so moved student disappears from other dropdowns
      setSelectedStudent((s) => ({ ...s, [groupId]: "" }));
    } catch (err: any) { toast.error(err.response?.data?.detail || "Failed to add student"); }
  };

  const removeStudent = async (groupId: string, studentId: string) => {
    try {
      await api.delete(`/groups/${groupId}/members/${studentId}`);
      setMembers((m) => ({ ...m, [groupId]: m[groupId].filter((s) => s.id !== studentId) }));
      await fetchStudents();
      toast.success("Student removed");
    } catch { toast.error("Failed to remove student"); }
  };

  const assignGroupToCourse = async (groupId: string) => {
    const courseId = assignCourse[groupId];
    if (!courseId) return;
    try {
      const r = await api.post(`/groups/courses/${courseId}/assign-group`, { group_id: groupId });
      toast.success(`${r.data.enrolled} students enrolled in course!`);
      setAssignCourse((a) => ({ ...a, [groupId]: "" }));
    } catch (err: any) { toast.error(err.response?.data?.detail || "Failed to assign group"); }
  };

  // Students not yet in any group (ungrouped) for the "add" dropdown
  const ungroupedStudents = allStudents.filter((s) => !s.group_id);
  // Students in a specific group's current members list (to avoid re-adding)
  const membersIds = (groupId: string) => new Set((members[groupId] || []).map((m) => m.id));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Groups</h1>
        {isTeacherOrAdmin && (
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700"
          >
            <Plus className="w-4 h-4" /> New group
          </button>
        )}
      </div>

      <p className="text-sm text-gray-500">
        Groups are class sections (e.g. "10A", "11B"). Assign a group to a course to auto-enroll all its students.
      </p>

      {/* Ungrouped students warning */}
      {isTeacherOrAdmin && ungroupedStudents.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl px-4 py-3 text-sm text-yellow-800">
          <strong>{ungroupedStudents.length} student{ungroupedStudents.length > 1 ? "s" : ""}</strong> not assigned to any group yet.
        </div>
      )}

      {/* Create group modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">New Group</h2>
              <button onClick={() => setShowCreate(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <form onSubmit={createGroup} className="space-y-3">
              <input
                placeholder="Group name (e.g. 10A)"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                required
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <div className="flex gap-3">
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                <button type="submit" className="flex-1 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700">Create</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Groups list */}
      <div className="space-y-3">
        {groups.map((group) => {
          const available = allStudents.filter(
            (s) => !s.group_id || s.group_id === group.id
              ? !membersIds(group.id).has(s.id)
              : false
          );

          return (
            <div key={group.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              {/* Header row */}
              <div
                className="px-5 py-4 flex items-center gap-3 cursor-pointer hover:bg-gray-50"
                onClick={() => toggleExpand(group.id)}
              >
                {expanded === group.id
                  ? <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
                  : <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />}
                <Users className="w-5 h-5 text-brand-500 flex-shrink-0" />
                <span className="font-semibold text-gray-900">{group.name}</span>
                {members[group.id] !== undefined && (
                  <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">
                    {members[group.id].length} students
                  </span>
                )}
              </div>

              {/* Expanded panel */}
              {expanded === group.id && (
                <div className="border-t border-gray-100 px-5 py-4 bg-gray-50 space-y-5">

                  {/* Member list */}
                  <div>
                    <h4 className="text-sm font-semibold text-gray-700 mb-2">Members</h4>
                    <div className="space-y-1 mb-3">
                      {(members[group.id] || []).map((s) => (
                        <div key={s.id} className="flex items-center justify-between bg-white px-3 py-2 rounded-lg border border-gray-100 text-sm">
                          <div className="flex items-center gap-2">
                            <div className="w-7 h-7 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-xs font-bold flex-shrink-0">
                              {s.full_name.charAt(0).toUpperCase()}
                            </div>
                            <div>
                              <p className="font-medium text-gray-800">{s.full_name}</p>
                              <p className="text-xs text-gray-400">{s.email}</p>
                            </div>
                          </div>
                          {isTeacherOrAdmin && (
                            <button
                              onClick={() => removeStudent(group.id, s.id)}
                              className="text-gray-300 hover:text-red-500 transition-colors ml-2 flex-shrink-0"
                              title="Remove from group"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      ))}
                      {(members[group.id] || []).length === 0 && (
                        <p className="text-sm text-gray-400 py-2">No students in this group yet.</p>
                      )}
                    </div>

                    {/* Add student dropdown */}
                    {isTeacherOrAdmin && (
                      <div className="flex gap-2">
                        <select
                          value={selectedStudent[group.id] || ""}
                          onChange={(e) => setSelectedStudent((s) => ({ ...s, [group.id]: e.target.value }))}
                          className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                        >
                          <option value="">Add a student…</option>
                          {allStudents
                            .filter((s) => !membersIds(group.id).has(s.id))
                            .map((s) => (
                              <option key={s.id} value={s.id}>
                                {s.full_name} — {s.email}{s.group_id ? " (in another group)" : ""}
                              </option>
                            ))}
                        </select>
                        <button
                          onClick={() => addStudent(group.id)}
                          disabled={!selectedStudent[group.id]}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700 disabled:opacity-40 transition-colors flex-shrink-0"
                        >
                          <UserPlus className="w-4 h-4" /> Add
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Assign group to course */}
                  {isTeacherOrAdmin && courses.length > 0 && (
                    <div className="border-t border-gray-200 pt-4">
                      <h4 className="text-sm font-semibold text-gray-700 mb-1">Enroll group in a course</h4>
                      <p className="text-xs text-gray-400 mb-2">All students in this group will be auto-enrolled instantly.</p>
                      <div className="flex gap-2">
                        <select
                          value={assignCourse[group.id] || ""}
                          onChange={(e) => setAssignCourse((a) => ({ ...a, [group.id]: e.target.value }))}
                          className="flex-1 px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 bg-white"
                        >
                          <option value="">Select course…</option>
                          {courses.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                        <button
                          onClick={() => assignGroupToCourse(group.id)}
                          disabled={!assignCourse[group.id]}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700 disabled:opacity-40 transition-colors flex-shrink-0"
                        >
                          <BookOpen className="w-4 h-4" /> Enroll
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {groups.length === 0 && (
          <div className="text-center py-16 text-gray-400">
            No groups yet. Create one to start organizing students.
          </div>
        )}
      </div>
    </div>
  );
}
