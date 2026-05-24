import uuid
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.models import UserRole, AttendanceStatus, SubmissionStatus


# ── Auth ──────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.student
    school_id: Optional[uuid.UUID] = None
    group_id: Optional[uuid.UUID] = None


# ── User ──────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    school_id: Optional[uuid.UUID]
    group_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── School ────────────────────────────────────────────────────────────────────

class SchoolCreate(BaseModel):
    name: str
    region: str
    city: str


class SchoolOut(BaseModel):
    id: uuid.UUID
    name: str
    region: str
    city: str

    model_config = {"from_attributes": True}


# ── Group ─────────────────────────────────────────────────────────────────────

class GroupCreate(BaseModel):
    name: str
    school_id: Optional[uuid.UUID] = None


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    school_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class AssignGroupRequest(BaseModel):
    group_id: uuid.UUID


class AssignStudentToGroupRequest(BaseModel):
    student_id: uuid.UUID


# ── Course ────────────────────────────────────────────────────────────────────

class CourseCreate(BaseModel):
    name: str
    description: Optional[str] = None
    school_id: Optional[uuid.UUID] = None


class CourseOut(BaseModel):
    id: uuid.UUID
    name: str
    description: Optional[str]
    teacher_id: uuid.UUID
    school_id: Optional[uuid.UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class EnrollRequest(BaseModel):
    student_id: uuid.UUID


class EnrollmentOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    course_id: uuid.UUID
    enrolled_at: datetime

    model_config = {"from_attributes": True}


# ── Assignment ────────────────────────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    title: str
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    max_score: float = 100.0


class AssignmentOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    title: str
    description: Optional[str]
    due_date: Optional[datetime]
    max_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Submission ────────────────────────────────────────────────────────────────

class SubmissionOut(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    student_id: uuid.UUID
    file_name: Optional[str]
    file_size: Optional[int]
    notes: Optional[str]
    status: SubmissionStatus
    submitted_at: datetime

    model_config = {"from_attributes": True}


class SubmissionWithDownload(SubmissionOut):
    download_url: Optional[str] = None
    score: Optional[float] = None
    max_score: Optional[float] = None
    feedback: Optional[str] = None


# ── Grade ─────────────────────────────────────────────────────────────────────

class GradeCreate(BaseModel):
    score: float
    feedback: Optional[str] = None


class GradeOut(BaseModel):
    id: uuid.UUID
    submission_id: uuid.UUID
    score: float
    max_score: float
    feedback: Optional[str]
    graded_by_id: Optional[uuid.UUID]
    is_ai_graded: bool
    graded_at: datetime

    model_config = {"from_attributes": True}


# ── Attendance ────────────────────────────────────────────────────────────────

class AttendanceRecordIn(BaseModel):
    student_id: uuid.UUID
    status: AttendanceStatus
    notes: Optional[str] = None


class AttendanceSessionCreate(BaseModel):
    session_date: date
    records: list[AttendanceRecordIn]


class AttendanceRecordOut(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    status: AttendanceStatus
    notes: Optional[str]

    model_config = {"from_attributes": True}


class AttendanceSessionOut(BaseModel):
    id: uuid.UUID
    course_id: uuid.UUID
    session_date: date
    created_at: datetime
    records: list[AttendanceRecordOut] = []

    model_config = {"from_attributes": True}


# ── Analytics (for regional comparison) ──────────────────────────────────────

class SchoolMetrics(BaseModel):
    school_id: uuid.UUID
    school_name: str
    region: str
    city: str
    avg_grade: Optional[float]
    attendance_rate: Optional[float]
    total_students: int
    total_courses: int
