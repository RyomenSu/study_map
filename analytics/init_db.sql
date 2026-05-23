CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE regions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE schools (
    id SERIAL PRIMARY KEY,
    region_id INT REFERENCES regions(id),
    name VARCHAR(200) NOT NULL
);

CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    school_id INT REFERENCES schools(id),
    name VARCHAR(200) NOT NULL,
    grade INT NOT NULL
);

CREATE TABLE submissions (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(id),
    subject VARCHAR(50) NOT NULL,
    total_score FLOAT NOT NULL,
    understanding_level VARCHAR(20),
    weak_topics JSONB DEFAULT '[]',
    strong_topics JSONB DEFAULT '[]',
    error_types JSONB DEFAULT '{}',
    exam_risk VARCHAR(20),
    assignment_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE predictions (
    id SERIAL PRIMARY KEY,
    student_id INT REFERENCES students(id),
    subject VARCHAR(50) NOT NULL,
    exam_pass_probability FLOAT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE regional_stats (
    id SERIAL PRIMARY KEY,
    region_id INT REFERENCES regions(id),
    subject VARCHAR(50) NOT NULL,
    avg_score FLOAT,
    weak_topics JSONB DEFAULT '[]',
    at_risk_count INT DEFAULT 0,
    trend FLOAT DEFAULT 0,
    month DATE NOT NULL
);

CREATE TABLE recommendations (
    id SERIAL PRIMARY KEY,
    region_id INT REFERENCES regions(id),
    school_id INT REFERENCES schools(id),
    level VARCHAR(20) NOT NULL, -- 'national', 'regional', 'school'
    content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_submissions_student ON submissions(student_id);
CREATE INDEX idx_submissions_created ON submissions(created_at);
CREATE INDEX idx_predictions_student ON predictions(student_id, subject);
CREATE INDEX idx_regional_stats_region ON regional_stats(region_id, month);
