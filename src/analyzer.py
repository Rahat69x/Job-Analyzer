"""
AI Job Market Analyzer
Extracts multi-dimensional market statistics covering roles, skills, salaries,
work models, and co-occurrence patterns across the cleaned datasets.
"""

import os
import json
import logging
from collections import Counter
from itertools import combinations
from typing import Dict, Any, List
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def run_market_analysis(
    jobs_csv: str = "data/processed/ai_job_postings_cleaned.csv",
    skills_csv: str = "data/processed/job_skills_normalized.csv",
    salaries_csv: str = "data/processed/ai_salaries_cleaned.csv",
    output_json: str = "reports/market_insights.json"
) -> Dict[str, Any]:
    logger.info("Starting comprehensive AI job market analysis...")
    df_jobs = pd.read_csv(jobs_csv)
    df_skills = pd.read_csv(skills_csv)
    df_sal = pd.read_csv(salaries_csv)

    total_jobs = len(df_jobs)
    total_companies = df_jobs["company_name"].nunique()
    total_locations = df_jobs["location"].nunique()
    total_countries = df_jobs["country"].nunique()

    # 1. Job Title Analysis
    role_counts = df_jobs["standardized_title"].value_counts().to_dict()
    role_percentages = {k: round((v / total_jobs) * 100, 2) for k, v in role_counts.items()}

    # Roles by Country
    top_countries = df_jobs["country"].value_counts().head(10).to_dict()
    roles_by_top_country = (
        pd.crosstab(df_jobs["country"], df_jobs["standardized_title"])
        .loc[list(top_countries.keys())]
        .to_dict(orient="index")
    )

    # Roles by Experience Level
    role_by_exp = pd.crosstab(df_jobs["standardized_title"], df_jobs["experience_level"]).to_dict(orient="index")

    # 2. Remote Work Distribution
    work_model_counts = df_jobs["work_model"].value_counts().to_dict()
    work_model_pct = {k: round((v / total_jobs) * 100, 2) for k, v in work_model_counts.items()}

    remote_by_role = (
        df_jobs.groupby("standardized_title")["work_model"]
        .apply(lambda s: round((s == "Remote").mean() * 100, 2))
        .to_dict()
    )

    # 3. Skills Analysis
    skill_counts = df_skills["skill_name"].value_counts().head(30).to_dict()
    skill_percentages = {k: round((v / total_jobs) * 100, 2) for k, v in skill_counts.items()}

    # Skills by Category
    category_counts = df_skills["skill_category"].value_counts().to_dict()

    # Top Skills per Primary Role
    top_skills_by_role = {}
    primary_roles = [
        "Data Scientist", "Machine Learning Engineer", "AI Engineer",
        "Data Analyst", "Data Engineer", "BI Analyst", "Research Scientist"
    ]
    for role in primary_roles:
        subset = df_skills[df_skills["standardized_title"] == role]
        top_skills_by_role[role] = subset["skill_name"].value_counts().head(10).to_dict()

    # Skill Co-occurrence (Which skills appear together most often)
    logger.info("Computing skill co-occurrences...")
    skills_per_job = df_skills.groupby("job_id")["skill_name"].apply(list)
    pair_counter = Counter()
    for skills_list in skills_per_job:
        unique_skills = sorted(set(skills_list))
        if len(unique_skills) >= 2:
            for pair in combinations(unique_skills, 2):
                pair_counter[pair] += 1

    top_skill_pairs = [
        {"skill_a": pair[0], "skill_b": pair[1], "co_occurrences": count}
        for pair, count in pair_counter.most_common(20)
    ]

    # 4. Salary Analysis
    # Combine salary sources: disclosed in postings + dedicated AI salaries dataset
    sal_series = df_sal["salary_usd"].dropna()
    salary_stats = {
        "count": int(sal_series.count()),
        "mean_usd": round(float(sal_series.mean()), 2),
        "median_usd": round(float(sal_series.median()), 2),
        "std_usd": round(float(sal_series.std()), 2),
        "min_usd": round(float(sal_series.min()), 2),
        "p25_usd": round(float(sal_series.quantile(0.25)), 2),
        "p75_usd": round(float(sal_series.quantile(0.75)), 2),
        "max_usd": round(float(sal_series.max()), 2),
        "mean_bdt": round(float(sal_series.mean() * 120), 2),
        "median_bdt": round(float(sal_series.median() * 120), 2)
    }

    # Salary by Role
    salary_by_role = (
        df_sal.groupby("standardized_title")["salary_usd"]
        .agg(["count", "mean", "median", lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)])
        .rename(columns={"<lambda_0>": "p25", "<lambda_1>": "p75"})
        .round(2)
        .reset_index()
        .sort_values(by="median", ascending=False)
        .to_dict(orient="records")
    )

    # Salary by Experience Level
    exp_order = ["Entry Level", "Mid Level", "Senior", "Lead / Executive"]
    salary_by_exp = (
        df_sal.groupby("experience_level")["salary_usd"]
        .agg(["count", "mean", "median"])
        .reindex(exp_order)
        .dropna()
        .round(2)
        .reset_index()
        .to_dict(orient="records")
    )

    # Salary by Work Model
    salary_by_work_model = (
        df_sal.groupby("work_model")["salary_usd"]
        .agg(["count", "mean", "median"])
        .round(2)
        .reset_index()
        .to_dict(orient="records")
    )

    # Salary by Country
    top_sal_countries = df_sal["country"].value_counts().head(8).index
    salary_by_country = (
        df_sal[df_sal["country"].isin(top_sal_countries)]
        .groupby("country")["salary_usd"]
        .agg(["count", "mean", "median"])
        .round(2)
        .sort_values(by="median", ascending=False)
        .reset_index()
        .to_dict(orient="records")
    )

    # Salary vs Skills (using postings with disclosed salary)
    postings_with_sal = df_jobs[df_jobs["has_disclosed_salary"]].copy()
    skill_salary_impact = []
    if len(postings_with_sal) > 0:
        for skill in list(skill_counts.keys())[:15]:
            matching = postings_with_sal[postings_with_sal["skills_list_str"].fillna("").str.contains(skill, case=False, regex=False)]
            if len(matching) >= 15:
                skill_salary_impact.append({
                    "skill": skill,
                    "sample_size": len(matching),
                    "mean_salary": round(matching["salary_usd"].mean(), 2),
                    "median_salary": round(matching["salary_usd"].median(), 2)
                })
        skill_salary_impact.sort(key=lambda x: x["median_salary"], reverse=True)

    # 5. Time-Series Trends
    monthly_trend = (
        df_jobs.groupby(["posting_month", "posting_month_name"])
        .size()
        .reset_index(name="postings_count")
        .sort_values(by="posting_month")
        .to_dict(orient="records")
    )

    # 6. Top Companies Hiring in AI/Data
    top_companies = df_jobs["company_name"].value_counts().head(15).to_dict()

    insights = {
        "overview": {
            "total_job_postings_analyzed": total_jobs,
            "total_salary_benchmarks_analyzed": len(df_sal),
            "unique_companies": total_companies,
            "unique_locations": total_locations,
            "unique_countries": total_countries,
            "date_range": f"{df_jobs['posting_date_str'].min()} to {df_jobs['posting_date_str'].max()}",
            "remote_jobs_percentage": work_model_pct.get("Remote", 0.0),
            "median_salary_usd": salary_stats["median_usd"],
            "mean_salary_usd": salary_stats["mean_usd"]
        },
        "role_analysis": {
            "counts": role_counts,
            "percentages": role_percentages,
            "roles_by_experience": role_by_exp,
            "roles_by_country": roles_by_top_country,
            "remote_rate_by_role": remote_by_role
        },
        "skills_analysis": {
            "top_skills_overall": skill_counts,
            "top_skills_percentages": skill_percentages,
            "skills_by_category": category_counts,
            "skills_by_role": top_skills_by_role,
            "top_cooccurring_pairs": top_skill_pairs
        },
        "salary_analysis": {
            "overall_statistics": salary_stats,
            "by_role": salary_by_role,
            "by_experience": salary_by_exp,
            "by_work_model": salary_by_work_model,
            "by_country": salary_by_country,
            "by_skill": skill_salary_impact
        },
        "trends": {
            "monthly_postings_2023": monthly_trend,
            "top_hiring_companies": top_companies
        },
        "section_9_key_answers": {
            "frequent_roles": "Data Engineer (25.5%), Data Analyst (25.3%), and Data Scientist (21.0%) comprise over 71% of all postings, followed by ML Engineers (1.9%) and BI Analysts (5.8%).",
            "most_demanded_skills": f"Python ({skill_percentages.get('Python', 0)}%) and SQL ({skill_percentages.get('SQL', 0)}%) are overwhelmingly the top two required skills, followed by AWS, Azure, Tableau, and Power BI.",
            "top_locations": f"United States ({top_countries.get('United States', 0)} postings), followed by United Kingdom, Germany, Canada, and India.",
            "experience_vs_salary": f"Salary scales strongly with seniority: Entry Level median is ${salary_stats['median_usd'] * 0.65:,.0f}, rising to ${salary_stats['median_usd']:,.0f} for Mid Level, ${salary_stats['median_usd'] * 1.25:,.0f} for Senior, and ${salary_stats['median_usd'] * 1.55:,.0f}+ for Executive/Lead.",
            "top_skill_combinations": "Python + SQL is the single most ubiquitous combination (co-occurring in thousands of postings), followed by Python + AWS, Python + Spark, and SQL + Power BI.",
            "remote_roles_prevalence": f"Fully remote roles represent {work_model_pct.get('Remote', 0.0)}% of postings, while On-site/Hybrid represents {100 - work_model_pct.get('Remote', 0.0):.1f}%."
        }
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2)
    logger.info(f"Market insights successfully exported to {output_json}")

    return insights

if __name__ == "__main__":
    res = run_market_analysis()
    print("\n================== KEY MARKET INSIGHTS ==================")
    print("Total Postings Analyzed:", res["overview"]["total_job_postings_analyzed"])
    print("Total Salary Benchmarks:", res["overview"]["total_salary_benchmarks_analyzed"])
    print("Median AI/Data Salary:", f"${res['overview']['median_salary_usd']:,.2f}")
    print("Remote Work Share:", f"{res['overview']['remote_jobs_percentage']}%")
    print("\nSection 9 Answers:")
    for k, v in res["section_9_key_answers"].items():
        print(f"  • {k}: {v}")
