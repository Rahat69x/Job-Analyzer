-- ==============================================================================
-- AI JOB MARKET ANALYTICS: RELATIONAL DATABASE SCHEMA
-- Compatible with PostgreSQL, MySQL, and SQLite
-- ==============================================================================

-- 1. Main Job Postings Table
CREATE TABLE IF NOT EXISTS ai_jobs (
    job_id VARCHAR(50) PRIMARY KEY,
    standardized_title VARCHAR(100) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    company_name VARCHAR(255) NOT NULL,
    location VARCHAR(255),
    country VARCHAR(100) NOT NULL,
    work_model VARCHAR(50) NOT NULL, -- Remote, Hybrid, On-site
    experience_level VARCHAR(50) NOT NULL, -- Entry Level, Mid Level, Senior, Lead / Executive
    employment_type VARCHAR(50) NOT NULL, -- Full-time, Contract, Part-time, Internship
    salary_usd NUMERIC(12, 2),
    salary_bdt NUMERIC(14, 2),
    has_disclosed_salary BOOLEAN NOT NULL DEFAULT FALSE,
    skills_list_str TEXT,
    skills_count INTEGER DEFAULT 0,
    posting_date_str DATE NOT NULL,
    posting_year INTEGER NOT NULL,
    posting_month INTEGER NOT NULL,
    posting_month_name VARCHAR(20) NOT NULL,
    job_via VARCHAR(100)
);

-- 2. Normalized Skills Mapping Table (Many-to-Many Relationship)
CREATE TABLE IF NOT EXISTS job_skills (
    id SERIAL PRIMARY KEY, -- For SQLite: INTEGER PRIMARY KEY AUTOINCREMENT
    job_id VARCHAR(50) NOT NULL,
    skill_name VARCHAR(100) NOT NULL,
    skill_category VARCHAR(100) NOT NULL,
    standardized_title VARCHAR(100) NOT NULL,
    experience_level VARCHAR(50) NOT NULL,
    work_model VARCHAR(50) NOT NULL,
    country VARCHAR(100) NOT NULL,
    CONSTRAINT fk_job FOREIGN KEY (job_id) REFERENCES ai_jobs(job_id) ON DELETE CASCADE
);

-- 3. Global AI & Data Science Salary Benchmarks Table
CREATE TABLE IF NOT EXISTS ai_salaries (
    id SERIAL PRIMARY KEY,
    work_year INTEGER NOT NULL,
    standardized_title VARCHAR(100) NOT NULL,
    job_title VARCHAR(255) NOT NULL,
    experience_level VARCHAR(50) NOT NULL,
    employment_type VARCHAR(50) NOT NULL,
    work_model VARCHAR(50) NOT NULL,
    salary_usd NUMERIC(12, 2) NOT NULL,
    salary_bdt NUMERIC(14, 2) NOT NULL,
    country VARCHAR(100) NOT NULL,
    company_size VARCHAR(10) NOT NULL
);

-- ==============================================================================
-- INDEXES FOR HIGH-PERFORMANCE ANALYTICAL QUERIES
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_jobs_title ON ai_jobs(standardized_title);
CREATE INDEX IF NOT EXISTS idx_jobs_country ON ai_jobs(country);
CREATE INDEX IF NOT EXISTS idx_jobs_work_model ON ai_jobs(work_model);
CREATE INDEX IF NOT EXISTS idx_jobs_exp ON ai_jobs(experience_level);
CREATE INDEX IF NOT EXISTS idx_jobs_posting_month ON ai_jobs(posting_month);
CREATE INDEX IF NOT EXISTS idx_jobs_salary ON ai_jobs(salary_usd);

CREATE INDEX IF NOT EXISTS idx_skills_name ON job_skills(skill_name);
CREATE INDEX IF NOT EXISTS idx_skills_job ON job_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_skills_cat ON job_skills(skill_category);
CREATE INDEX IF NOT EXISTS idx_skills_role ON job_skills(standardized_title);

CREATE INDEX IF NOT EXISTS idx_sal_year ON ai_salaries(work_year);
CREATE INDEX IF NOT EXISTS idx_sal_title ON ai_salaries(standardized_title);
CREATE INDEX IF NOT EXISTS idx_sal_exp ON ai_salaries(experience_level);
CREATE INDEX IF NOT EXISTS idx_sal_country ON ai_salaries(country);
