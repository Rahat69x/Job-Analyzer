"""
Data Cleaning and Preprocessing Pipeline
Standardizes job titles, cleans experience levels, parses skills,
normalizes locations and salaries, and formats dates.
"""

import os
import ast
import re
import json
import logging
from typing import List, Dict, Any, Tuple
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

SKILL_NAME_MAP = {
    "python": "Python",
    "sql": "SQL",
    "r": "R",
    "java": "Java",
    "c++": "C++",
    "c#": "C#",
    "scala": "Scala",
    "julia": "Julia",
    "go": "Go",
    "bash": "Bash",
    "sas": "SAS",
    "matlab": "MATLAB",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "html": "HTML",
    "css": "CSS",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-learn",
    "sklearn": "Scikit-learn",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "keras": "Keras",
    "spark": "Spark",
    "pyspark": "PySpark",
    "hadoop": "Hadoop",
    "airflow": "Airflow",
    "kafka": "Kafka",
    "hugging face": "Hugging Face",
    "huggingface": "Hugging Face",
    "langchain": "LangChain",
    "openai": "OpenAI API",
    "opencv": "OpenCV",
    "nltk": "NLTK",
    "spacy": "spaCy",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "power bi": "Power BI",
    "powerbi": "Power BI",
    "tableau": "Tableau",
    "excel": "Excel",
    "looker": "Looker",
    "qlik": "Qlik",
    "dax": "DAX",
    "ssis": "SSIS",
    "ssrs": "SSRS",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "snowflake": "Snowflake",
    "bigquery": "BigQuery",
    "redshift": "Redshift",
    "databricks": "Databricks",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "git": "Git",
    "github": "GitHub",
    "gitlab": "GitLab",
    "ci/cd": "CI/CD",
    "jenkins": "Jenkins",
    "terraform": "Terraform",
    "linux": "Linux",
    "postgresql": "PostgreSQL",
    "mysql": "MySQL",
    "sql server": "SQL Server",
    "oracle": "Oracle",
    "mongodb": "MongoDB",
    "nosql": "NoSQL",
    "redis": "Redis",
    "elasticsearch": "Elasticsearch",
    "cassandra": "Cassandra"
}

SKILL_CATEGORY_MAP = {
    "Python": "Programming Languages",
    "SQL": "Programming Languages",
    "R": "Programming Languages",
    "Java": "Programming Languages",
    "C++": "Programming Languages",
    "C#": "Programming Languages",
    "Scala": "Programming Languages",
    "Julia": "Programming Languages",
    "Go": "Programming Languages",
    "Bash": "Programming Languages",
    "SAS": "Programming Languages",
    "MATLAB": "Programming Languages",
    "JavaScript": "Programming Languages",
    "TypeScript": "Programming Languages",
    "Pandas": "Libraries & Frameworks",
    "NumPy": "Libraries & Frameworks",
    "Scikit-learn": "Libraries & Frameworks",
    "TensorFlow": "Libraries & Frameworks",
    "PyTorch": "Libraries & Frameworks",
    "Keras": "Libraries & Frameworks",
    "XGBoost": "Libraries & Frameworks",
    "LightGBM": "Libraries & Frameworks",
    "Hugging Face": "Libraries & Frameworks",
    "LangChain": "Libraries & Frameworks",
    "OpenAI API": "Libraries & Frameworks",
    "OpenCV": "Libraries & Frameworks",
    "NLTK": "Libraries & Frameworks",
    "spaCy": "Libraries & Frameworks",
    "Power BI": "BI & Data Visualization",
    "Tableau": "BI & Data Visualization",
    "Excel": "BI & Data Visualization",
    "Looker": "BI & Data Visualization",
    "Qlik": "BI & Data Visualization",
    "DAX": "BI & Data Visualization",
    "SSIS": "BI & Data Visualization",
    "SSRS": "BI & Data Visualization",
    "AWS": "Cloud & Distributed Systems",
    "Azure": "Cloud & Distributed Systems",
    "GCP": "Cloud & Distributed Systems",
    "Snowflake": "Cloud & Distributed Systems",
    "BigQuery": "Cloud & Distributed Systems",
    "Redshift": "Cloud & Distributed Systems",
    "Databricks": "Cloud & Distributed Systems",
    "Spark": "Cloud & Distributed Systems",
    "PySpark": "Cloud & Distributed Systems",
    "Hadoop": "Cloud & Distributed Systems",
    "Airflow": "Cloud & Distributed Systems",
    "Kafka": "Cloud & Distributed Systems",
    "PostgreSQL": "Databases",
    "MySQL": "Databases",
    "SQL Server": "Databases",
    "Oracle": "Databases",
    "MongoDB": "Databases",
    "NoSQL": "Databases",
    "Redis": "Databases",
    "Elasticsearch": "Databases",
    "Cassandra": "Databases",
    "Docker": "DevOps & Infrastructure",
    "Kubernetes": "DevOps & Infrastructure",
    "Git": "DevOps & Infrastructure",
    "GitHub": "DevOps & Infrastructure",
    "GitLab": "DevOps & Infrastructure",
    "Jenkins": "DevOps & Infrastructure",
    "Terraform": "DevOps & Infrastructure",
    "Linux": "DevOps & Infrastructure",
    "CI/CD": "DevOps & Infrastructure"
}

def standardize_job_title(title: str, short_title: str = "") -> str:
    combined = f"{short_title} {title}".lower()
    
    if any(k in combined for k in ["machine learning", "ml engineer", "mlops", "deep learning"]):
        return "Machine Learning Engineer"
    if any(k in combined for k in ["ai engineer", "artificial intelligence", "genai", "generative ai", "llm", "prompt"]):
        return "AI Engineer"
    if any(k in combined for k in ["data scientist", "data science", "statistician"]):
        return "Data Scientist"
    if any(k in combined for k in ["business intelligence", "bi analyst", "bi engineer", "bi developer", "power bi developer"]):
        return "BI Analyst"
    if any(k in combined for k in ["data analyst", "analytics analyst", "reporting analyst", "data specialist"]):
        return "Data Analyst"
    if any(k in combined for k in ["data engineer", "data pipeline", "etl", "database engineer", "big data engineer"]):
        return "Data Engineer"
    if any(k in combined for k in ["research scientist", "ai researcher"]):
        return "Research Scientist"
    if any(k in combined for k in ["data architect", "cloud architect", "solutions architect", "ai architect"]):
        return "Cloud & Data Architect"
    if any(k in combined for k in ["software engineer", "backend developer", "developer"]):
        return "Software Engineer (Data/AI)"
    if "business analyst" in combined:
        return "Business Analyst"

    if short_title:
        return short_title
    return "Other AI / Data Role"

def parse_experience_level(title: str, exp_col: str = "") -> str:
    if exp_col and str(exp_col).upper() in ["EN", "ENTRY", "JUNIOR", "INTERN"]:
        return "Entry Level"
    if exp_col and str(exp_col).upper() in ["MI", "MID", "INTERMEDIATE"]:
        return "Mid Level"
    if exp_col and str(exp_col).upper() in ["SE", "SENIOR", "SR"]:
        return "Senior"
    if exp_col and str(exp_col).upper() in ["EX", "EXECUTIVE", "LEAD", "DIRECTOR", "PRINCIPAL", "HEAD"]:
        return "Lead / Executive"

    t = (title or "").lower()
    if any(w in t for w in ["junior", "jr", "entry", "intern", "associate", "graduate", "trainee"]):
        return "Entry Level"
    if any(w in t for w in ["lead", "principal", "staff", "director", "head", "manager", "architect", "vp"]):
        return "Lead / Executive"
    if any(w in t for w in ["senior", "sr", "sr.", "experienced"]):
        return "Senior"
    
    return "Mid Level"

def parse_skills_string(skills_str: Any) -> List[str]:
    if pd.isna(skills_str) or not skills_str:
        return []
    
    raw_list = []
    if isinstance(skills_str, list):
        raw_list = skills_str
    elif isinstance(skills_str, str):
        skills_str = skills_str.strip()
        if skills_str.startswith("[") and skills_str.endswith("]"):
            try:
                raw_list = ast.literal_eval(skills_str)
            except Exception:
                raw_list = [s.strip("'\" ") for s in skills_str[1:-1].split(",") if s.strip()]
        else:
            raw_list = [s.strip() for s in skills_str.split(",") if s.strip()]

    standardized = []
    for item in raw_list:
        clean = str(item).lower().strip()
        mapped = SKILL_NAME_MAP.get(clean, clean.title())
        if mapped not in standardized:
            standardized.append(mapped)

    return standardized

def clean_data_jobs_raw(input_path: str, output_path: str, skills_output_path: str) -> pd.DataFrame:
    logger.info(f"Loading raw job postings from {input_path}")
    df = pd.read_csv(input_path)
    initial_rows = len(df)

    # 1. Deduplication
    df = df.drop_duplicates(subset=["company_name", "job_title", "job_location", "job_posted_date"])
    deduped_rows = len(df)
    logger.info(f"Deduplicated {initial_rows - deduped_rows} redundant postings. Remaining: {deduped_rows}")

    # 2. Standardize Titles
    df["standardized_title"] = df.apply(
        lambda r: standardize_job_title(str(r.get("job_title", "")), str(r.get("job_title_short", ""))),
        axis=1
    )

    # 3. Clean Experience Level
    df["experience_level"] = df["job_title"].apply(parse_experience_level)

    # 4. Clean Remote Work Type
    def classify_work_model(row):
        wfh = row.get("job_work_from_home", False)
        loc = str(row.get("job_location", "")).lower()
        if wfh is True or "anywhere" in loc or "remote" in loc or "work from home" in loc:
            return "Remote"
        if "hybrid" in loc:
            return "Hybrid"
        return "On-site"

    df["work_model"] = df.apply(classify_work_model, axis=1)

    # 5. Clean Employment Type
    def clean_schedule(sched):
        s = str(sched).lower()
        if "part" in s:
            return "Part-time"
        if "contract" in s or "temp" in s:
            return "Contract"
        if "intern" in s:
            return "Internship"
        return "Full-time"

    df["employment_type"] = df["job_schedule_type"].apply(clean_schedule)

    # 6. Clean and parse skills
    df["parsed_skills"] = df["job_skills"].apply(parse_skills_string)
    df["skills_count"] = df["parsed_skills"].apply(len)
    df["skills_list_str"] = df["parsed_skills"].apply(lambda lst: ", ".join(lst))

    # 7. Clean and parse posting dates
    df["posted_date"] = pd.to_datetime(df["job_posted_date"], errors="coerce")
    df["posting_date_str"] = df["posted_date"].dt.strftime("%Y-%m-%d")
    df["posting_year"] = df["posted_date"].dt.year.fillna(2023).astype(int)
    df["posting_month"] = df["posted_date"].dt.month.fillna(1).astype(int)
    df["posting_month_name"] = df["posted_date"].dt.strftime("%b")

    # 8. Clean Locations
    df["country"] = df["job_country"].fillna("Worldwide").replace({"": "Worldwide"})
    df["location"] = df["job_location"].fillna(df["country"]).replace({"": "Worldwide"})
    df["company_name"] = df["company_name"].fillna("Confidential Employer")

    # 9. Normalize Salaries (disclosed only)
    df["salary_usd"] = pd.to_numeric(df["salary_year_avg"], errors="coerce")
    # Clean out extreme statistical artifacts if present
    df.loc[(df["salary_usd"] < 15000) | (df["salary_usd"] > 900000), "salary_usd"] = np.nan
    df["salary_bdt"] = df["salary_usd"].apply(lambda v: round(v * 120) if pd.notnull(v) else np.nan)
    df["has_disclosed_salary"] = df["salary_usd"].notnull()

    # Assign synthetic unique Job IDs
    df["job_id"] = [f"JOB-{i+10001}" for i in range(len(df))]

    # Final column subset
    clean_cols = [
        "job_id", "standardized_title", "job_title", "company_name",
        "location", "country", "work_model", "experience_level", "employment_type",
        "salary_usd", "salary_bdt", "has_disclosed_salary",
        "skills_list_str", "skills_count",
        "posting_date_str", "posting_year", "posting_month", "posting_month_name",
        "job_via"
    ]
    cleaned_df = df[clean_cols].copy()
    cleaned_df.to_csv(output_path, index=False)
    logger.info(f"Saved cleaned job postings to {output_path} with {len(cleaned_df)} rows")

    # Unpivot / normalize skills table for relational database and Power BI
    skills_rows = []
    for _, row in df.iterrows():
        jid = row["job_id"]
        for sk in row["parsed_skills"]:
            cat = SKILL_CATEGORY_MAP.get(sk, "Other Technologies")
            skills_rows.append({
                "job_id": jid,
                "skill_name": sk,
                "skill_category": cat,
                "standardized_title": row["standardized_title"],
                "experience_level": row["experience_level"],
                "work_model": row["work_model"],
                "country": row["country"]
            })

    skills_df = pd.DataFrame(skills_rows)
    skills_df.to_csv(skills_output_path, index=False)
    logger.info(f"Saved normalized job skills table to {skills_output_path} with {len(skills_df)} skill entries")

    return cleaned_df

def clean_ai_salaries(input_path: str, output_path: str) -> pd.DataFrame:
    logger.info(f"Loading raw AI salaries from {input_path}")
    df = pd.read_csv(input_path)
    initial_rows = len(df)

    # 1. Deduplication
    df = df.drop_duplicates()
    logger.info(f"Deduplicated salaries from {initial_rows} to {len(df)} rows")

    # 2. Standardize Titles
    df["standardized_title"] = df["job_title"].apply(lambda t: standardize_job_title(str(t)))

    # 3. Clean Experience Level
    df["experience_level"] = df.apply(lambda r: parse_experience_level(str(r["job_title"]), str(r["experience_level"])), axis=1)

    # 4. Clean Remote Work
    def map_remote(ratio):
        if ratio == 100:
            return "Remote"
        elif ratio == 50:
            return "Hybrid"
        return "On-site"

    df["work_model"] = df["remote_ratio"].apply(map_remote)

    # 5. Clean Employment Type
    emp_map = {
        "FT": "Full-time",
        "PT": "Part-time",
        "CT": "Contract",
        "FL": "Freelance"
    }
    df["employment_type"] = df["employment_type"].map(emp_map).fillna("Full-time")

    # 6. Calculate BDT equivalent
    df["salary_usd"] = df["salary_in_usd"]
    df["salary_bdt"] = (df["salary_usd"] * 120).round()

    # 7. Map company location codes to full country names where applicable
    country_code_map = {
        "US": "United States",
        "GB": "United Kingdom",
        "CA": "Canada",
        "DE": "Germany",
        "IN": "India",
        "FR": "France",
        "ES": "Spain",
        "AU": "Australia",
        "NL": "Netherlands",
        "BR": "Brazil",
        "BD": "Bangladesh",
        "SG": "Singapore"
    }
    df["country"] = df["company_location"].map(lambda c: country_code_map.get(c, c))

    # Keep relevant subset
    sal_cols = [
        "work_year", "standardized_title", "job_title", "experience_level",
        "employment_type", "work_model", "salary_usd", "salary_bdt",
        "country", "company_size"
    ]
    clean_sal = df[sal_cols].copy()
    clean_sal.to_csv(output_path, index=False)
    logger.info(f"Saved cleaned AI salaries to {output_path} with {len(clean_sal)} records")
    return clean_sal

if __name__ == "__main__":
    raw_jobs = "data/raw/data_jobs_raw.csv"
    raw_salaries = "data/raw/ai_jobs_salaries.csv"
    out_jobs = "data/processed/ai_job_postings_cleaned.csv"
    out_skills = "data/processed/job_skills_normalized.csv"
    out_salaries = "data/processed/ai_salaries_cleaned.csv"

    os.makedirs("data/processed", exist_ok=True)
    clean_data_jobs_raw(raw_jobs, out_jobs, out_skills)
    clean_ai_salaries(raw_salaries, out_salaries)
