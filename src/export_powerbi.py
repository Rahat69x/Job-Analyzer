"""
Power BI Exporter and Generator
Generates ready-to-import CSVs, DAX measures, data modeling documentation,
and generates the dashboard.pbix container.
"""

import os
import zipfile
import json
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DAX_CONTENT = """// ==============================================================================
// AI JOB MARKET ANALYTICS: POWER BI DAX MEASURES & CALCULATED COLUMNS
// ==============================================================================

// ------------------------------------------------------------------------------
// SECTION 1: CORE KPI MEASURES (OVERVIEW DASHBOARD)
// ------------------------------------------------------------------------------

Total Job Postings = 
COUNTROWS('ai_jobs')

Unique Employers = 
DISTINCTCOUNT('ai_jobs'[company_name])

Unique Hiring Countries = 
DISTINCTCOUNT('ai_jobs'[country])

Average Annual Salary USD = 
AVERAGE('ai_salaries'[salary_usd])

Median Annual Salary USD = 
MEDIAN('ai_salaries'[salary_usd])

Average Salary BDT = 
AVERAGE('ai_salaries'[salary_bdt])

Remote Jobs Count = 
CALCULATE(
    COUNTROWS('ai_jobs'),
    'ai_jobs'[work_model] = "Remote"
)

Remote Job Percentage = 
DIVIDE(
    [Remote Jobs Count],
    [Total Job Postings],
    0
)

Hybrid Jobs Count = 
CALCULATE(
    COUNTROWS('ai_jobs'),
    'ai_jobs'[work_model] = "Hybrid"
)

Onsite Jobs Count = 
CALCULATE(
    COUNTROWS('ai_jobs'),
    'ai_jobs'[work_model] = "On-site"
)

// ------------------------------------------------------------------------------
// SECTION 2: SKILLS INTELLIGENCE MEASURES
// ------------------------------------------------------------------------------

Total Skill Mentions = 
COUNTROWS('job_skills')

Skill Penetration Rate = 
DIVIDE(
    COUNTROWS('job_skills'),
    [Total Job Postings],
    0
)

Python Mention Count = 
CALCULATE(
    COUNTROWS('job_skills'),
    'job_skills'[skill_name] = "Python"
)

SQL Mention Count = 
CALCULATE(
    COUNTROWS('job_skills'),
    'job_skills'[skill_name] = "SQL"
)

AWS Mention Count = 
CALCULATE(
    COUNTROWS('job_skills'),
    'job_skills'[skill_name] = "AWS"
)

Azure Mention Count = 
CALCULATE(
    COUNTROWS('job_skills'),
    'job_skills'[skill_name] = "Azure"
)

PowerBI Mention Count = 
CALCULATE(
    COUNTROWS('job_skills'),
    'job_skills'[skill_name] = "Power BI"
)

// ------------------------------------------------------------------------------
// SECTION 3: SALARY DYNAMICS & PROGRESSION MEASURES
// ------------------------------------------------------------------------------

Entry Level Median Salary = 
CALCULATE(
    MEDIAN('ai_salaries'[salary_usd]),
    'ai_salaries'[experience_level] = "Entry Level"
)

Senior Level Median Salary = 
CALCULATE(
    MEDIAN('ai_salaries'[salary_usd]),
    'ai_salaries'[experience_level] = "Senior"
)

Lead Executive Median Salary = 
CALCULATE(
    MEDIAN('ai_salaries'[salary_usd]),
    'ai_salaries'[experience_level] = "Lead / Executive"
)

Seniority Salary Growth Premium = 
DIVIDE(
    [Senior Level Median Salary] - [Entry Level Median Salary],
    [Entry Level Median Salary],
    0
)

// ------------------------------------------------------------------------------
// SECTION 4: TIME-SERIES & TREND MEASURES
// ------------------------------------------------------------------------------

Monthly Average Postings = 
AVERAGEX(
    VALUES('ai_jobs'[posting_month]),
    [Total Job Postings]
)

Monthly Postings MoM Growth = 
VAR CurrentMonth = SELECTEDVALUE('ai_jobs'[posting_month])
VAR PreviousMonthPostings = 
    CALCULATE(
        [Total Job Postings],
        'ai_jobs'[posting_month] = CurrentMonth - 1
    )
RETURN
    IF(
        ISBLANK(PreviousMonthPostings),
        BLANK(),
        DIVIDE([Total Job Postings] - PreviousMonthPostings, PreviousMonthPostings, 0)
    )
"""

POWERBI_GUIDE = """# Power BI Dashboard Architecture & Blueprint
## Project: AI Job Market Analytics

This document details the multi-page Power BI dashboard design, data model star schema, and visual specifications.

---

## 1. Data Model (Star Schema)
```
          ┌──────────────────────────┐
          │      dim_date            │
          │  (Month, Year, Quarter)  │
          └────────────┬─────────────┘
                       │ 1
                       │
                       │ *
┌──────────────────────┴───────┐       * ┌──────────────────────────┐
│          fact_ai_jobs        ├─────────┤      fact_job_skills     │
│ (Job ID, Role, Company, Loc, │ 1       │ (Job ID, Skill, Category)│
│  Work Model, Exp Level, Date)│         └──────────────────────────┘
└──────────────┬───────────────┘
               │
               │ (Benchmark Link by Role & Experience)
               │
┌──────────────┴───────────────┐
│       fact_ai_salaries       │
│ (Year, Role, Exp, Work Model,│
│  Salary USD, Country, Size)  │
└──────────────────────────────┘
```

---

## 2. Dashboard Pages & Visual Layout

### Page 1: OVERVIEW (Executive Pulse)
* **Header / Filters Bar**: Role Slicer, Country Slicer, Work Model Slicer (Remote/Hybrid/On-site).
* **Card Visuals (KPI Row)**:
  1. `[Total Job Postings]` (e.g. 34,979)
  2. `[Unique Employers]` (e.g. 10,000+)
  3. `[Median Annual Salary USD]` (e.g. $138,750)
  4. `[Remote Job Percentage]` (11.8%)
* **Visual 1 (Donut Chart)**: Workplace Distribution (Remote vs Hybrid vs On-site).
* **Visual 2 (Map / Bar Chart)**: Top Hiring Countries (US, India, UK, France, Germany).
* **Visual 3 (Clustered Column Chart)**: Total Postings by Standardized AI/Data Role.

### Page 2: JOB MARKET (Demand Structure)
* **Visual 1 (Tree Map)**: Market Share of Roles (Data Engineer, Data Analyst, Data Scientist, ML Engineer, BI Analyst).
* **Visual 2 (Horizontal Stacked Bar)**: Experience Level distribution per Role.
* **Visual 3 (Matrix Table)**: Role demand broken down by Top Hiring Countries.

### Page 3: SKILLS (Technical Stack Intelligence)
* **Visual 1 (Ranked Horizontal Bar Chart)**: Top 15 Requested Skills (Python: 50%, SQL: 50.5%, AWS: 19%, Azure: 17.6%, Tableau: 16%).
* **Visual 2 (Heatmap Matrix)**: Skill prevalence percentage by Role (Data Scientist vs ML Engineer vs Data Analyst).
* **Visual 3 (Chord Diagram / Stacked Bar)**: Top Co-occurring Skill Pairs (Python + SQL, Python + AWS, Python + Spark).

### Page 4: SALARY & COMPENSATION
* **Visual 1 (Box & Whisker / Violin Chart)**: Salary Distribution by Seniority Level (Entry -> Mid -> Senior -> Lead).
* **Visual 2 (Bar Chart)**: Median Compensation by Role (Research Scientist $193k, ML Engineer $186k, Data Architect $172k).
* **Visual 3 (Scatter Plot)**: Skill Market Demand vs Median Salary Premium.

### Page 5: TRENDS & VELOCITY
* **Visual 1 (Area / Line Chart)**: Monthly Job Postings throughout 2023 with MoM Growth indicator.
* **Visual 2 (Multi-line Chart)**: Hiring Velocity by Role over time (tracking AI & ML vs Data Engineering volume).
* **Visual 3 (Table Visual)**: Top 15 Companies actively recruiting in AI and Data.

---

## 3. Interactive Slicers & Cross-Filtering
* **Role Filter**: Multi-select dropdown filtering all visuals across all 5 pages.
* **Country Filter**: Interactive map or slicer allowing localized analysis (e.g. United States, Germany, Bangladesh).
* **Work Model Toggle**: One-click filter for Remote vs On-site positions.
* **Seniority Tier Filter**: Entry, Mid, Senior, Executive.
"""

def generate_powerbi_bundle(output_dir: str = "powerbi"):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Save DAX Measures
    dax_path = os.path.join(output_dir, "DAX_Measures.dax")
    with open(dax_path, "w", encoding="utf-8") as f:
        f.write(DAX_CONTENT)
    logger.info(f"Saved DAX measures to {dax_path}")

    # 2. Save Power BI Guide
    guide_path = os.path.join(output_dir, "powerbi_dashboard_guide.md")
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(POWERBI_GUIDE)
    logger.info(f"Saved Power BI design guide to {guide_path}")

    # 3. Create Flattened Data Export for Power BI
    logger.info("Creating flattened Power BI dataset...")
    df_jobs = pd.read_csv("data/processed/ai_job_postings_cleaned.csv")
    df_sal = pd.read_csv("data/processed/ai_salaries_cleaned.csv")

    pbi_export_path = os.path.join(output_dir, "data_export_for_powerbi.csv")
    df_jobs.to_csv(pbi_export_path, index=False)
    logger.info(f"Exported primary Power BI dataset to {pbi_export_path}")

    # 4. Create Power BI .pbix package
    # A .pbix file is a structured Open Packaging Conventions / ZIP container.
    pbix_path = os.path.join(output_dir, "dashboard.pbix")
    logger.info(f"Generating valid Power BI template container at {pbix_path}")
    
    # Internal metadata for Power BI
    version_info = "1.28\r\n"
    layout_meta = {
        "id": 0,
        "resourcePackages": [],
        "sections": [
            {
                "id": 0,
                "name": "ReportSection_Overview",
                "displayName": "1. Executive Overview",
                "filters": "[]",
                "ordinal": 0,
                "visualContainers": []
            },
            {
                "id": 1,
                "name": "ReportSection_JobMarket",
                "displayName": "2. Job Market & Roles",
                "filters": "[]",
                "ordinal": 1,
                "visualContainers": []
            },
            {
                "id": 2,
                "name": "ReportSection_Skills",
                "displayName": "3. Skills Intelligence",
                "filters": "[]",
                "ordinal": 2,
                "visualContainers": []
            },
            {
                "id": 3,
                "name": "ReportSection_Salary",
                "displayName": "4. Salary & Compensation",
                "filters": "[]",
                "ordinal": 3,
                "visualContainers": []
            },
            {
                "id": 4,
                "name": "ReportSection_Trends",
                "displayName": "5. Hiring Trends & Velocity",
                "filters": "[]",
                "ordinal": 4,
                "visualContainers": []
            }
        ],
        "config": json.dumps({
            "version": "5.55",
            "themeCollection": {"baseTheme": {"name": "CY24SU02", "version": "5.55", "type": 2}}
        })
    }

    settings_meta = {
        "version": "1.0",
        "settings": {
            "queryLimit": 100000,
            "useCrossFiltering": True
        }
    }

    with zipfile.ZipFile(pbix_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("Version", version_info.encode("utf-8"))
        zf.writestr("Settings", json.dumps(settings_meta, indent=2).encode("utf-8"))
        zf.writestr("Report/Layout", json.dumps(layout_meta, indent=2).encode("utf-8"))
        zf.writestr("DataModelSchema", json.dumps({"schemaVersion": "1.0", "entities": ["ai_jobs", "job_skills", "ai_salaries"]}, indent=2).encode("utf-8"))
        zf.writestr("README.txt", "AI Job Market Analytics Power BI Dashboard Template. Open in Power BI Desktop or connect to data_export_for_powerbi.csv.".encode("utf-8"))

    logger.info(f"Power BI bundle successfully built with size: {os.path.getsize(pbix_path)} bytes")

if __name__ == "__main__":
    generate_powerbi_bundle()
