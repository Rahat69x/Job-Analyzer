"""
Visualization Generation Script for AI Job Market Analytics
Produces publication-grade figures using Matplotlib and Seaborn.
"""

import os
import ast
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Aesthetic configuration
sns.set_theme(style="whitegrid", palette="muted")
plt.rcParams.update({
    "font.sans-serif": "DejaVu Sans",
    "font.family": "sans-serif",
    "figure.titlesize": 16,
    "axes.titlesize": 14,
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "figure.autolayout": True,
    "figure.dpi": 300
})

COLORS = {
    "primary": "#4f46e5",    # Indigo
    "secondary": "#06b6d4",  # Cyan
    "accent": "#f59e0b",     # Amber
    "success": "#10b981",    # Emerald
    "danger": "#ef4444",     # Rose
    "dark": "#1e293b",       # Slate 800
    "light": "#f8fafc"       # Slate 50
}

def generate_all_figures(
    jobs_csv: str = "data/processed/ai_job_postings_cleaned.csv",
    skills_csv: str = "data/processed/job_skills_normalized.csv",
    salaries_csv: str = "data/processed/ai_salaries_cleaned.csv",
    output_dir: str = "reports/figures"
):
    os.makedirs(output_dir, exist_ok=True)
    df_jobs = pd.read_csv(jobs_csv)
    df_skills = pd.read_csv(skills_csv)
    df_sal = pd.read_csv(salaries_csv)

    # ==================== Figure 1: Top AI/Data Job Roles ====================
    logger.info("Generating Figure 1: Top Job Roles...")
    fig, ax = plt.subplots(figsize=(10, 6))
    role_counts = df_jobs["standardized_title"].value_counts().head(10)
    sns.barplot(x=role_counts.values, y=role_counts.index, color=COLORS["primary"], ax=ax)
    ax.set_title("Most In-Demand AI & Data Job Roles (2023–2024)", weight="bold", pad=15)
    ax.set_xlabel("Number of Job Postings")
    ax.set_ylabel("")
    for i, v in enumerate(role_counts.values):
        ax.text(v + 80, i, f"{v:,} ({v/len(df_jobs)*100:.1f}%)", va="center", fontsize=9, color=COLORS["dark"])
    ax.set_xlim(0, max(role_counts.values) * 1.18)
    fig.savefig(os.path.join(output_dir, "fig1_top_ai_roles.png"))
    plt.close(fig)

    # ==================== Figure 2: Top Skills Overall ====================
    logger.info("Generating Figure 2: Top Skills Overall...")
    fig, ax = plt.subplots(figsize=(11, 7))
    top_skills = df_skills["skill_name"].value_counts().head(15)
    sns.barplot(x=top_skills.values, y=top_skills.index, palette="viridis", hue=top_skills.index, legend=False, ax=ax)
    ax.set_title("Top 15 Most Requested Skills Across All AI/Data Roles", weight="bold", pad=15)
    ax.set_xlabel("Skill Mention Frequency")
    ax.set_ylabel("")
    total_postings = len(df_jobs)
    for i, v in enumerate(top_skills.values):
        ax.text(v + 150, i, f"{v:,} ({v/total_postings*100:.1f}%)", va="center", fontsize=9)
    ax.set_xlim(0, max(top_skills.values) * 1.15)
    fig.savefig(os.path.join(output_dir, "fig2_top_skills_overall.png"))
    plt.close(fig)

    # ==================== Figure 3: Skills by Role Heatmap ====================
    logger.info("Generating Figure 3: Skills by Role Heatmap...")
    target_roles = [
        "Data Scientist", "Machine Learning Engineer", "AI Engineer",
        "Data Analyst", "Data Engineer", "BI Analyst"
    ]
    target_skills = [
        "Python", "SQL", "R", "Pandas", "NumPy", "Scikit-learn",
        "TensorFlow", "PyTorch", "AWS", "Azure", "GCP", "Spark",
        "Tableau", "Power BI", "Excel", "Docker"
    ]
    subset = df_skills[df_skills["standardized_title"].isin(target_roles) & df_skills["skill_name"].isin(target_skills)]
    ct = pd.crosstab(subset["skill_name"], subset["standardized_title"])
    # Normalize by total jobs in each role to get percentage
    role_totals = df_jobs[df_jobs["standardized_title"].isin(target_roles)]["standardized_title"].value_counts()
    ct_pct = (ct / role_totals * 100).fillna(0).loc[target_skills, target_roles]

    fig, ax = plt.subplots(figsize=(11, 8))
    sns.heatmap(ct_pct, annot=True, fmt=".1f", cmap="YlGnBu", cbar_kws={'label': '% of Postings Requiring Skill'}, ax=ax)
    ax.set_title("Skill Prevalence by Primary AI/Data Role (%)", weight="bold", pad=15)
    ax.set_xlabel("Job Role")
    ax.set_ylabel("Skill")
    plt.xticks(rotation=25, ha="right")
    fig.savefig(os.path.join(output_dir, "fig3_skills_by_role_heatmap.png"))
    plt.close(fig)

    # ==================== Figure 4: Salary Distribution ====================
    logger.info("Generating Figure 4: Salary Distribution...")
    fig, ax = plt.subplots(figsize=(10, 6))
    salaries = df_sal["salary_usd"].dropna()
    sns.histplot(salaries, kde=True, bins=45, color=COLORS["primary"], ax=ax)
    median_sal = salaries.median()
    mean_sal = salaries.mean()
    ax.axvline(median_sal, color=COLORS["danger"], linestyle="--", linewidth=2, label=f"Median: ${median_sal:,.0f}")
    ax.axvline(mean_sal, color=COLORS["accent"], linestyle=":", linewidth=2, label=f"Mean: ${mean_sal:,.0f}")
    ax.set_title("Global AI & Data Science Annual Salary Distribution (USD)", weight="bold", pad=15)
    ax.set_xlabel("Annual Salary in USD ($)")
    ax.set_ylabel("Job Postings Count")
    ax.legend(frameon=True)
    ax.set_xlim(20000, 450000)
    fig.savefig(os.path.join(output_dir, "fig4_salary_distribution.png"))
    plt.close(fig)

    # ==================== Figure 5: Salary by Experience Level ====================
    logger.info("Generating Figure 5: Salary by Experience...")
    fig, ax = plt.subplots(figsize=(10, 6))
    exp_order = ["Entry Level", "Mid Level", "Senior", "Lead / Executive"]
    sns.boxplot(
        data=df_sal[df_sal["experience_level"].isin(exp_order)],
        x="experience_level", y="salary_usd", order=exp_order,
        palette="Blues", hue="experience_level", legend=False,
        showmeans=True, meanprops={"marker":"o", "markerfacecolor":"red", "markeredgecolor":"red"},
        ax=ax
    )
    ax.set_title("AI / Data Science Salary Progression by Experience Tier", weight="bold", pad=15)
    ax.set_xlabel("Seniority Level")
    ax.set_ylabel("Annual Compensation (USD)")
    ax.set_ylim(20000, 380000)
    fig.savefig(os.path.join(output_dir, "fig5_salary_by_experience.png"))
    plt.close(fig)

    # ==================== Figure 6: Salary by Job Title ====================
    logger.info("Generating Figure 6: Salary by Job Title...")
    top_sal_roles = df_sal["standardized_title"].value_counts().head(8).index
    role_sal_summary = (
        df_sal[df_sal["standardized_title"].isin(top_sal_roles)]
        .groupby("standardized_title")["salary_usd"]
        .median()
        .sort_values(ascending=True)
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    sns.barplot(x=role_sal_summary.values, y=role_sal_summary.index, color=COLORS["secondary"], ax=ax)
    ax.set_title("Median Annual Salary by Key AI/Data Role (USD)", weight="bold", pad=15)
    ax.set_xlabel("Median Annual Salary ($)")
    ax.set_ylabel("")
    for i, v in enumerate(role_sal_summary.values):
        ax.text(v + 2000, i, f"${v:,.0f}", va="center", fontsize=9, weight="bold")
    ax.set_xlim(0, max(role_sal_summary.values) * 1.15)
    fig.savefig(os.path.join(output_dir, "fig6_salary_by_role.png"))
    plt.close(fig)

    # ==================== Figure 7: Remote Work Distribution ====================
    logger.info("Generating Figure 7: Remote Work Distribution...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6))
    
    # Donut chart
    work_counts = df_jobs["work_model"].value_counts()
    ax1.pie(
        work_counts.values, labels=work_counts.index, autopct="%1.1f%%",
        startangle=140, colors=[COLORS["primary"], COLORS["accent"], COLORS["success"]],
        wedgeprops=dict(width=0.45, edgecolor='w')
    )
    ax1.set_title("Workplace Distribution", weight="bold")

    # Remote rate by role
    remote_role = (
        df_jobs.groupby("standardized_title")["work_model"]
        .apply(lambda s: (s == "Remote").mean() * 100)
        .loc[target_roles]
        .sort_values()
    )
    sns.barplot(x=remote_role.values, y=remote_role.index, color=COLORS["success"], ax=ax2)
    ax2.set_title("Remote Role Percentage by Job Title (%)", weight="bold")
    ax2.set_xlabel("% Fully Remote")
    ax2.set_ylabel("")
    for i, v in enumerate(remote_role.values):
        ax2.text(v + 0.3, i, f"{v:.1f}%", va="center", fontsize=9)
    ax2.set_xlim(0, max(remote_role.values) * 1.25)
    
    fig.suptitle("Remote Work Landscape in AI & Data Science", fontsize=15, weight="bold")
    fig.savefig(os.path.join(output_dir, "fig7_remote_work_share.png"))
    plt.close(fig)

    # ==================== Figure 8: Monthly Hiring Trends ====================
    logger.info("Generating Figure 8: Monthly Hiring Trends...")
    fig, ax = plt.subplots(figsize=(11, 5))
    monthly = df_jobs.groupby("posting_month").size()
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    ax.plot(month_names, monthly.values, marker="o", linewidth=2.5, color=COLORS["primary"], markersize=8)
    ax.fill_between(month_names, monthly.values, alpha=0.15, color=COLORS["primary"])
    ax.set_title("2023 AI & Data Job Postings Hiring Velocity Over Time", weight="bold", pad=15)
    ax.set_xlabel("Posting Month")
    ax.set_ylabel("Monthly Job Openings")
    for x, y in zip(month_names, monthly.values):
        ax.annotate(f"{y:,}", (x, y), textcoords="offset points", xytext=(0, 10), ha="center", fontsize=8.5, weight="bold")
    ax.set_ylim(min(monthly.values) * 0.85, max(monthly.values) * 1.15)
    fig.savefig(os.path.join(output_dir, "fig8_monthly_hiring_trends.png"))
    plt.close(fig)

    # ==================== Figure 9: Skill Co-occurrence ====================
    logger.info("Generating Figure 9: Skill Co-occurrence...")
    from collections import Counter
    from itertools import combinations
    skills_per_job = df_skills.groupby("job_id")["skill_name"].apply(list)
    pair_counter = Counter()
    for s_list in skills_per_job:
        for pair in combinations(sorted(set(s_list)), 2):
            pair_counter[pair] += 1
    
    top_pairs = pair_counter.most_common(10)
    labels = [f"{p[0]} + {p[1]}" for p, _ in top_pairs]
    counts = [c for _, c in top_pairs]

    fig, ax = plt.subplots(figsize=(11, 6))
    sns.barplot(x=counts, y=labels, color=COLORS["accent"], ax=ax)
    ax.set_title("Top 10 Most Common Skill Combinations Required Together", weight="bold", pad=15)
    ax.set_xlabel("Number of Job Postings Requiring Both Skills")
    ax.set_ylabel("")
    for i, v in enumerate(counts):
        ax.text(v + 100, i, f"{v:,} jobs", va="center", fontsize=9)
    ax.set_xlim(0, max(counts) * 1.15)
    fig.savefig(os.path.join(output_dir, "fig9_skill_cooccurrence.png"))
    plt.close(fig)

    logger.info(f"All 9 publication-grade figures successfully generated in {output_dir}")

if __name__ == "__main__":
    generate_all_figures()
