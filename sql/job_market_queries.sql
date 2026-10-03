-- ==============================================================================
-- AI JOB MARKET ANALYTICS: CORE ANALYTICAL SQL QUERIES
-- Designed for PostgreSQL / MySQL / SQLite
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- QUERY 1: Most Demanded Job Titles
-- Calculates the total count and market share percentage for each AI/Data role.
-- ------------------------------------------------------------------------------
SELECT 
    standardized_title AS job_role,
    COUNT(*) AS total_postings,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ai_jobs), 2) AS market_share_percentage
FROM ai_jobs
GROUP BY standardized_title
ORDER BY total_postings DESC;


-- ------------------------------------------------------------------------------
-- QUERY 2: Top 15 Most Demanded Skills Overall
-- Identifies the most sought-after technical skills across the entire job market.
-- ------------------------------------------------------------------------------
SELECT 
    skill_name,
    skill_category,
    COUNT(*) AS demand_frequency,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(DISTINCT job_id) FROM ai_jobs), 2) AS percentage_of_postings
FROM job_skills
GROUP BY skill_name, skill_category
ORDER BY demand_frequency DESC
LIMIT 15;


-- ------------------------------------------------------------------------------
-- QUERY 3: Job Postings Distribution by Location & Country
-- Ranks top hiring geographic regions and assesses global AI market demand.
-- ------------------------------------------------------------------------------
SELECT 
    country,
    COUNT(*) AS total_openings,
    COUNT(DISTINCT company_name) AS unique_employers,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM ai_jobs), 2) AS global_market_share_pct
FROM ai_jobs
GROUP BY country
ORDER BY total_openings DESC
LIMIT 15;


-- ------------------------------------------------------------------------------
-- QUERY 4: Average and Median Salary by Role
-- Evaluates compensation metrics across standardized AI, ML, and Data roles.
-- ------------------------------------------------------------------------------
SELECT 
    standardized_title AS job_role,
    COUNT(*) AS sample_size,
    ROUND(AVG(salary_usd), 2) AS avg_salary_usd,
    ROUND(AVG(salary_bdt), 2) AS avg_salary_bdt,
    ROUND(MIN(salary_usd), 2) AS min_salary_usd,
    ROUND(MAX(salary_usd), 2) AS max_salary_usd
FROM ai_salaries
GROUP BY standardized_title
HAVING COUNT(*) >= 50
ORDER BY avg_salary_usd DESC;


-- ------------------------------------------------------------------------------
-- QUERY 5: Salary Progression by Experience Level
-- Analyzes how seniority impacts compensation in the AI and Data domain.
-- ------------------------------------------------------------------------------
SELECT 
    experience_level,
    COUNT(*) AS records_count,
    ROUND(AVG(salary_usd), 2) AS avg_salary_usd,
    ROUND(AVG(salary_bdt), 2) AS avg_salary_bdt,
    ROUND(MIN(salary_usd), 2) AS min_salary_usd,
    ROUND(MAX(salary_usd), 2) AS max_salary_usd
FROM ai_salaries
GROUP BY experience_level
ORDER BY 
    CASE experience_level
        WHEN 'Entry Level' THEN 1
        WHEN 'Mid Level' THEN 2
        WHEN 'Senior' THEN 3
        WHEN 'Lead / Executive' THEN 4
        ELSE 5
    END;


-- ------------------------------------------------------------------------------
-- QUERY 6: Remote Job Percentage Overall and by Role
-- Measures workplace flexibility and remote availability for AI/Data specialists.
-- ------------------------------------------------------------------------------
SELECT 
    standardized_title AS job_role,
    COUNT(*) AS total_postings,
    SUM(CASE WHEN work_model = 'Remote' THEN 1 ELSE 0 END) AS remote_postings,
    SUM(CASE WHEN work_model = 'Hybrid' THEN 1 ELSE 0 END) AS hybrid_postings,
    SUM(CASE WHEN work_model = 'On-site' THEN 1 ELSE 0 END) AS onsite_postings,
    ROUND(SUM(CASE WHEN work_model = 'Remote' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS remote_percentage
FROM ai_jobs
GROUP BY standardized_title
ORDER BY total_postings DESC;


-- ------------------------------------------------------------------------------
-- QUERY 7: Skill Frequency by Specific AI/Data Job Role
-- Demonstrates required skill stacks across Data Scientists, ML Engineers, and Analysts.
-- ------------------------------------------------------------------------------
WITH RoleSkillCounts AS (
    SELECT 
        standardized_title,
        skill_name,
        COUNT(*) AS skill_count,
        ROW_NUMBER() OVER(PARTITION BY standardized_title ORDER BY COUNT(*) DESC) AS skill_rank
    FROM job_skills
    WHERE standardized_title IN ('Data Scientist', 'Machine Learning Engineer', 'Data Analyst', 'Data Engineer', 'AI Engineer')
    GROUP BY standardized_title, skill_name
)
SELECT 
    standardized_title AS job_role,
    skill_rank,
    skill_name,
    skill_count
FROM RoleSkillCounts
WHERE skill_rank <= 5
ORDER BY standardized_title, skill_rank;


-- ------------------------------------------------------------------------------
-- QUERY 8: Job-Title Hiring Trends Over Time (Monthly Velocity)
-- Tracks posting volume trajectory across the 12 months of the year.
-- ------------------------------------------------------------------------------
SELECT 
    posting_month,
    posting_month_name AS month_name,
    COUNT(*) AS total_postings,
    COUNT(CASE WHEN standardized_title = 'Data Scientist' THEN 1 END) AS data_scientist_postings,
    COUNT(CASE WHEN standardized_title = 'Data Engineer' THEN 1 END) AS data_engineer_postings,
    COUNT(CASE WHEN standardized_title = 'Data Analyst' THEN 1 END) AS data_analyst_postings,
    COUNT(CASE WHEN standardized_title = 'Machine Learning Engineer' THEN 1 END) AS ml_engineer_postings
FROM ai_jobs
GROUP BY posting_month, posting_month_name
ORDER BY posting_month ASC;


-- ------------------------------------------------------------------------------
-- QUERY 9: Top Co-Occurring Skill Pairs (Skill Combinations)
-- Computes the most frequent technical pairs appearing together on job requisitions.
-- ------------------------------------------------------------------------------
SELECT 
    s1.skill_name AS skill_a,
    s2.skill_name AS skill_b,
    COUNT(*) AS co_occurrence_count
FROM job_skills s1
JOIN job_skills s2 
    ON s1.job_id = s2.job_id 
   AND s1.skill_name < s2.skill_name
GROUP BY s1.skill_name, s2.skill_name
ORDER BY co_occurrence_count DESC
LIMIT 10;


-- ------------------------------------------------------------------------------
-- QUERY 10: High-Paying Skills vs Skill Demand Volume
-- Cross-examines skill market demand with disclosed salary benchmarks.
-- ------------------------------------------------------------------------------
SELECT 
    js.skill_name,
    COUNT(DISTINCT j.job_id) AS total_postings_with_skill,
    ROUND(AVG(j.salary_usd), 2) AS avg_disclosed_salary_usd
FROM ai_jobs j
JOIN job_skills js ON j.job_id = js.job_id
WHERE j.salary_usd IS NOT NULL AND j.salary_usd > 20000
GROUP BY js.skill_name
HAVING COUNT(DISTINCT j.job_id) >= 20
ORDER BY avg_disclosed_salary_usd DESC
LIMIT 12;
