export type Role = "student" | "teacher" | "admin";
export type AttendanceStatus = "present" | "absent" | "late" | "excused";
export type SubmissionStatus = "submitted" | "graded" | "late";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: Role;
  school_id: string | null;
  group_id: string | null;
  created_at: string;
}

export interface Group {
  id: string;
  name: string;
  school_id: string | null;
  created_at: string;
}

export interface School {
  id: string;
  name: string;
  region: string;
  city: string;
}

export interface Course {
  id: string;
  name: string;
  description: string | null;
  teacher_id: string;
  school_id: string | null;
  created_at: string;
}

export interface Assignment {
  id: string;
  course_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  max_score: number;
  created_at: string;
}

export interface Submission {
  id: string;
  assignment_id: string;
  student_id: string;
  file_name: string | null;
  file_size: number | null;
  notes: string | null;
  status: SubmissionStatus;
  submitted_at: string;
  download_url?: string;
  score?: number | null;
  max_score?: number | null;
  feedback?: string | null;
}

export interface Grade {
  id: string;
  submission_id: string;
  score: number;
  max_score: number;
  feedback: string | null;
  graded_by_id: string;
  graded_at: string;
}

export interface AttendanceRecord {
  id: string;
  student_id: string;
  status: AttendanceStatus;
  notes: string | null;
}

export interface AttendanceSession {
  id: string;
  course_id: string;
  session_date: string;
  created_at: string;
  records: AttendanceRecord[];
}

export interface SchoolMetrics {
  school_id: string;
  school_name: string;
  region: string;
  city: string;
  avg_grade: number | null;
  attendance_rate: number | null;
  total_students: number;
  total_courses: number;
}
