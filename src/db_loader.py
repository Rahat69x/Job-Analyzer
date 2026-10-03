"""
Database Loader and SQL Validation Script
Initializes relational database tables, bulk-loads cleaned data,
and runs the SQL query suite to verify syntax and analytical outputs.
"""

import os
import sqlite3
import logging
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = "data/ai_market_analytics.db"
SCHEMA_PATH = "sql/schema.sql"
QUERIES_PATH = "sql/job_market_queries.sql"

def init_and_load_db(
    db_path: str = DB_PATH,
    jobs_csv: str = "data/processed/ai_job_postings_cleaned.csv",
    skills_csv: str = "data/processed/job_skills_normalized.csv",
    salaries_csv: str = "data/processed/ai_salaries_cleaned.csv"
):
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Removed existing database at {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create SQLite-compatible schema
    logger.info("Creating relational tables...")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_jobs (
        job_id TEXT PRIMARY KEY,
        standardized_title TEXT NOT NULL,
        job_title TEXT NOT NULL,
        company_name TEXT NOT NULL,
        location TEXT,
        country TEXT NOT NULL,
        work_model TEXT NOT NULL,
        experience_level TEXT NOT NULL,
        employment_type TEXT NOT NULL,
        salary_usd REAL,
        salary_bdt REAL,
        has_disclosed_salary INTEGER NOT NULL DEFAULT 0,
        skills_list_str TEXT,
        skills_count INTEGER DEFAULT 0,
        posting_date_str TEXT NOT NULL,
        posting_year INTEGER NOT NULL,
        posting_month INTEGER NOT NULL,
        posting_month_name TEXT NOT NULL,
        job_via TEXT
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_skills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id TEXT NOT NULL,
        skill_name TEXT NOT NULL,
        skill_category TEXT NOT NULL,
        standardized_title TEXT NOT NULL,
        experience_level TEXT NOT NULL,
        work_model TEXT NOT NULL,
        country TEXT NOT NULL,
        FOREIGN KEY (job_id) REFERENCES ai_jobs(job_id)
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ai_salaries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        work_year INTEGER NOT NULL,
        standardized_title TEXT NOT NULL,
        job_title TEXT NOT NULL,
        experience_level TEXT NOT NULL,
        employment_type TEXT NOT NULL,
        work_model TEXT NOT NULL,
        salary_usd REAL NOT NULL,
        salary_bdt REAL NOT NULL,
        country TEXT NOT NULL,
        company_size TEXT NOT NULL
    );
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_title ON ai_jobs(standardized_title);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jobs_country ON ai_jobs(country);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_skills_name ON job_skills(skill_name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sal_title ON ai_salaries(standardized_title);")
    conn.commit()

    # Load dataframes into SQLite
    logger.info("Loading ai_jobs...")
    df_jobs = pd.read_csv(jobs_csv)
    df_jobs["has_disclosed_salary"] = df_jobs["has_disclosed_salary"].astype(int)
    df_jobs.to_sql("ai_jobs", conn, if_exists="append", index=False)

    logger.info("Loading job_skills...")
    df_skills = pd.read_csv(skills_csv)
    df_skills.to_sql("job_skills", conn, if_exists="append", index=False)

    logger.info("Loading ai_salaries...")
    df_sal = pd.read_csv(salaries_csv)
    df_sal.to_sql("ai_salaries", conn, if_exists="append", index=False)

    logger.info("Database loaded successfully!")
    logger.info(f"Counts: ai_jobs={len(df_jobs)}, job_skills={len(df_skills)}, ai_salaries={len(df_sal)}")
    conn.close()

def run_sql_query_validation(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    with open(QUERIES_PATH, "r", encoding="utf-8") as f:
        full_sql = f.read()

    # Extract individual queries separated by comment banners
    raw_queries = full_sql.split("------------------------------------------------------------------------------")
    
    print("\n================== SQL QUERY VALIDATION EXECUTION ==================\n")
    query_num = 1
    for block in raw_queries:
        lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not lines:
            continue
        
        # Extract title and sql body
        title = lines[0].replace("--", "").strip() if lines[0].startswith("--") else f"Query {query_num}"
        sql_lines = [l for l in lines if not l.startswith("--")]
        sql_text = "\n".join(sql_lines).strip()
        if not sql_text.upper().startswith("SELECT") and not sql_text.upper().startswith("WITH"):
            continue

        print(f">>> Running: {title}")
        try:
            df_res = pd.read_sql_query(sql_text, conn)
            print(df_res.head(5).to_string(index=False))
            print(f"Total rows returned: {len(df_res)}\n")
            query_num += 1
        except Exception as e:
            print(f"Execution Error in {title}: {e}\n")

    conn.close()

if __name__ == "__main__":
    init_and_load_db()
    run_sql_query_validation()
