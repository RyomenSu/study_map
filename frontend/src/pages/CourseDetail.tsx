import { useEffect, useState, useRef } from "react";
import { useParams } from "react-router-dom";
import { FileText, Plus, Upload, Check, X, Download } from "lucide-react";
import toast from "react-hot-toast";
import { api } from "../api/client";
import { useAuth } from "../store/auth";
import type { Assignment, Course, Submission } from "../types";

type Tab = "assignments" | "grades";

export function CourseDetail() {
  const { courseId } = useParams<{ courseId: string }>();
  const { user } = useAuth();
  const [course, setCourse] = useState<Course | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [tab, setTab] = useState<Tab>("assignments");
  const [showCreate, setShowCreate] = useState(false);
  const [newAssignment, setNewAssignment] = useState({ title: "", description: "", due_date: "", max_score: 100 });
  const [grades, setGrades] = useState<any[]>([]);
  const [submissions, setSubmissions] = useState<Record<string, Submission[]>>({});

  const isTeacherOrAdmin = user?.role === "teacher" || user?.role === "admin";

  useEffect(() => {
    api.get(`/courses/${courseId}`)
      .then((r) => setCourse(r.data))
      .catch(() => toast.error("Failed to load course"));
    fetchAssignments();
  }, [courseId]);

  const fetchAssignments = () =>
    api.get(`/courses/${courseId}/assignments`)
      .then((r) => setAssignments(r.data))
      .catch(() => toast.error("Failed to load assignments"));

  const fetchGrades = () =>
    api.get(`/courses/${courseId}/grades`).then((r) => setGrades(r.data));

  const fetchSubmissions = async (assignmentId: string) => {
    const r = await api.get(`/courses/${courseId}/assignments/${assignmentId}/submissions`);
    setSubmissions((prev) => ({ ...prev, [assignmentId]: r.data }));
  };

  useEffect(() => {
    if (tab === "grades") fetchGrades();
  }, [tab]);

  const createAssignment = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post(`/courses/${courseId}/assignments`, {
        ...newAssignment,
        due_date: newAssignment.due_date || null,
        max_score: Number(newAssignment.max_score),
      });
      toast.success("Assignment created!");
      setShowCreate(false);
      fetchAssignments();
    } catch {
      toast.error("Failed to create assignment");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">{course?.name}</h1>
        {course?.description && <p className="text-gray-500 mt-1">{course.description}</p>}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-6">
          {(["assignments", "grades"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`pb-3 text-sm font-medium capitalize border-b-2 transition-colors ${
                tab === t ? "border-brand-600 text-brand-600" : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t}
            </button>
          ))}
        </nav>
      </div>

      {tab === "assignments" && (
        <div className="space-y-4">
          {isTeacherOrAdmin && (
            <button
              onClick={() => setShowCreate(true)}
              className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm font-medium hover:bg-brand-700"
            >
              <Plus className="w-4 h-4" /> New assignment
            </button>
          )}

          {/* Create assignment modal */}
          {showCreate && (
            <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold">New Assignment</h2>
                  <button onClick={() => setShowCreate(false)}><X className="w-5 h-5 text-gray-400" /></button>
                </div>
                <form onSubmit={createAssignment} className="space-y-3">
                  <input
                    placeholder="Title"
                    value={newAssignment.title}
                    onChange={(e) => setNewAssignment((f) => ({ ...f, title: e.target.value }))}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <textarea
                    placeholder="Description (optional)"
                    value={newAssignment.description}
                    onChange={(e) => setNewAssignment((f) => ({ ...f, description: e.target.value }))}
                    rows={2}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                  />
                  <div className="flex gap-3">
                    <input
                      type="datetime-local"
                      value={newAssignment.due_date}
                      onChange={(e) => setNewAssignment((f) => ({ ...f, due_date: e.target.value }))}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                    <input
                      type="number"
                      placeholder="Max pts"
                      value={newAssignment.max_score}
                      onChange={(e) => setNewAssignment((f) => ({ ...f, max_score: Number(e.target.value) }))}
                      className="w-24 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
                    />
                  </div>
                  <div className="flex gap-3 pt-1">
                    <button type="button" onClick={() => setShowCreate(false)} className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-sm hover:bg-gray-50">Cancel</button>
                    <button type="submit" className="flex-1 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700">Create</button>
                  </div>
                </form>
              </div>
            </div>
          )}

          {assignments.map((a) => (
            <AssignmentCard
              key={a.id}
              assignment={a}
              courseId={courseId!}
              isTeacherOrAdmin={isTeacherOrAdmin}
              submissions={submissions[a.id] || []}
              onExpand={() => fetchSubmissions(a.id)}
              currentUserId={user?.id || ""}
            />
          ))}
          {assignments.length === 0 && (
            <div className="text-center py-12 text-gray-400">No assignments yet.</div>
          )}
        </div>
      )}

      {tab === "grades" && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Assignment</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Student</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Score</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Status</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Feedback</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {grades.map((g) => (
                <GradeRow key={g.submission_id} grade={g} isTeacher={isTeacherOrAdmin} />
              ))}
              {grades.length === 0 && (
                <tr><td colSpan={5} className="text-center py-10 text-gray-400">No grades yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function AssignmentCard({
  assignment, courseId, isTeacherOrAdmin, submissions, onExpand, currentUserId,
}: {
  assignment: Assignment;
  courseId: string;
  isTeacherOrAdmin: boolean;
  submissions: Submission[];
  onExpand: () => void;
  currentUserId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notes, setNotes] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const toggle = () => {
    if (!expanded) onExpand();
    setExpanded((v) => !v);
  };

  const submitFile = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploading(true);
    try {
      const formData = new FormData();
      if (fileRef.current?.files?.[0]) formData.append("file", fileRef.current.files[0]);
      if (notes) formData.append("notes", notes);
      await api.post(`/courses/${courseId}/assignments/${assignment.id}/submit`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success("Submitted!");
      onExpand();
      setNotes("");
      if (fileRef.current) fileRef.current.value = "";
    } catch {
      toast.error("Submission failed");
    } finally {
      setUploading(false);
    }
  };

  const grade = async (submissionId: string, score: number, feedback: string) => {
    try {
      await api.post(`/submissions/${submissionId}/grade`, { score, feedback });
      toast.success("Graded!");
      onExpand();
    } catch {
      await api.put(`/submissions/${submissionId}/grade`, { score, feedback });
      toast.success("Grade updated!");
      onExpand();
    }
  };

  const mySubmission = submissions.find((s) => s.student_id === currentUserId);
  const isOverdue = assignment.due_date && new Date(assignment.due_date) < new Date();

  return (
    <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
      <div className="px-5 py-4 flex items-start justify-between cursor-pointer hover:bg-gray-50" onClick={toggle}>
        <div className="flex items-start gap-3">
          <FileText className="w-5 h-5 text-gray-400 mt-0.5 flex-shrink-0" />
          <div>
            <h3 className="font-medium text-gray-900">{assignment.title}</h3>
            {assignment.description && <p className="text-sm text-gray-500 mt-0.5">{assignment.description}</p>}
            <div className="flex items-center gap-3 mt-1">
              {assignment.due_date && (
                <span className={`text-xs ${isOverdue ? "text-red-500" : "text-gray-400"}`}>
                  Due {new Date(assignment.due_date).toLocaleString()}
                </span>
              )}
              <span className="text-xs text-gray-400">{assignment.max_score} pts</span>
              {mySubmission && (
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  mySubmission.status === "graded" ? "bg-green-100 text-green-700" :
                  mySubmission.status === "late" ? "bg-red-100 text-red-700" :
                  "bg-blue-100 text-blue-700"
                }`}>
                  {mySubmission.status}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-gray-100 px-5 py-4 bg-gray-50 space-y-4">
          {/* Student upload form */}
          {!isTeacherOrAdmin && !mySubmission && (
            <form onSubmit={submitFile} className="space-y-3">
              <h4 className="text-sm font-medium text-gray-700">Submit your work</h4>
              <input type="file" ref={fileRef} className="block w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100" />
              <input
                placeholder="Notes (optional)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <button type="submit" disabled={uploading} className="flex items-center gap-2 px-4 py-2 bg-brand-600 text-white rounded-lg text-sm hover:bg-brand-700 disabled:opacity-60">
                <Upload className="w-4 h-4" /> {uploading ? "Uploading..." : "Submit"}
              </button>
            </form>
          )}

          {/* Submissions list (teacher or own) */}
          {submissions.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-sm font-medium text-gray-700">
                {isTeacherOrAdmin ? `Submissions (${submissions.length})` : "Your submission"}
              </h4>
              {submissions.map((s) => (
                <SubmissionRow
                  key={s.id}
                  submission={s}
                  maxScore={assignment.max_score}
                  isTeacher={isTeacherOrAdmin}
                  onGrade={grade}
                />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SubmissionRow({
  submission, maxScore, isTeacher, onGrade,
}: {
  submission: Submission;
  maxScore: number;
  isTeacher: boolean;
  onGrade: (id: string, score: number, feedback: string) => void;
}) {
  const [grading, setGrading] = useState(false);
  const [score, setScore] = useState("");
  const [feedback, setFeedback] = useState("");

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-3 text-sm">
      <div className="flex items-center justify-between">
        <div>
          <span className="font-medium text-gray-700">{submission.file_name || "No file"}</span>
          {submission.notes && <p className="text-gray-500 text-xs mt-0.5">{submission.notes}</p>}
          <span className={`text-xs mt-1 inline-block px-2 py-0.5 rounded-full font-medium ${
            submission.status === "graded" ? "bg-green-100 text-green-700" :
            submission.status === "late" ? "bg-red-100 text-red-700" :
            "bg-blue-100 text-blue-700"
          }`}>
            {submission.status}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {submission.download_url && (
            <a href={submission.download_url} target="_blank" rel="noreferrer"
              className="p-1.5 text-gray-500 hover:text-brand-600 hover:bg-brand-50 rounded-lg"
            >
              <Download className="w-4 h-4" />
            </a>
          )}
          {isTeacher && (
            <button onClick={() => setGrading((v) => !v)} className="px-2 py-1 text-xs bg-brand-50 text-brand-700 rounded-lg hover:bg-brand-100">
              Grade
            </button>
          )}
        </div>
      </div>

      {grading && isTeacher && (
        <div className="mt-3 flex items-center gap-2">
          <input
            type="number"
            placeholder={`Score / ${maxScore}`}
            value={score}
            onChange={(e) => setScore(e.target.value)}
            className="w-28 px-2 py-1 border border-gray-300 rounded text-sm"
          />
          <input
            placeholder="Feedback"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
          />
          <button
            onClick={() => { onGrade(submission.id, Number(score), feedback); setGrading(false); }}
            className="p-1.5 bg-green-500 text-white rounded hover:bg-green-600"
          >
            <Check className="w-4 h-4" />
          </button>
          <button onClick={() => setGrading(false)} className="p-1.5 text-gray-400 hover:text-gray-600 rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

function GradeRow({ grade, isTeacher }: { grade: any; isTeacher: boolean }) {
  const pct = grade.score != null ? Math.round((grade.score / grade.max_score) * 100) : null;
  return (
    <tr>
      <td className="px-4 py-3 text-gray-600 font-mono text-xs">{grade.assignment_id.slice(0, 8)}</td>
      <td className="px-4 py-3 text-gray-600 font-mono text-xs">{grade.student_id.slice(0, 8)}</td>
      <td className="px-4 py-3">
        {grade.score != null ? (
          <span className={`font-semibold ${pct! >= 70 ? "text-green-600" : pct! >= 50 ? "text-yellow-600" : "text-red-600"}`}>
            {grade.score} / {grade.max_score} ({pct}%)
          </span>
        ) : <span className="text-gray-400">—</span>}
      </td>
      <td className="px-4 py-3">
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
          grade.status === "graded" ? "bg-green-100 text-green-700" :
          grade.status === "late" ? "bg-red-100 text-red-700" :
          "bg-blue-100 text-blue-700"
        }`}>{grade.status}</span>
      </td>
      <td className="px-4 py-3 text-gray-500 text-xs">{grade.feedback || "—"}</td>
    </tr>
  );
}
