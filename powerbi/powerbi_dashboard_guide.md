# Power BI Dashboard Architecture & Blueprint
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
