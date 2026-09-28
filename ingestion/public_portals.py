from typing import List, Optional
from datetime import datetime, timezone, timedelta
from core.models import NormalizedJob, CompanyInfo, SalaryInfo, ExperienceRequirement

def get_partner_job_registry() -> dict:
    now = datetime.now(timezone.utc)
    return {
        8: [  # IT/Telecommunication
            NormalizedJob(
                id="skilljobs-801",
                source="Skill.jobs",
                title="Senior DevOps & Infrastructure Engineer",
                company=CompanyInfo(name="Therap (BD) Ltd.", tier="MNC", verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                location="Dhaka",
                publish_date=now - timedelta(days=2),
                deadline=now + timedelta(days=15),
                experience=ExperienceRequirement(min_years=4.0, max_years=7.0, raw_text="4 to 7 years"),
                salary=SalaryInfo(disclosed=True, min_salary=110000, max_salary=150000, raw_text="Tk. 110,000 - 150,000", salary_bdt_min=1320000, salary_bdt_max=1800000, salary_usd_min=11000, salary_usd_max=15000),
                job_context="Looking for an experienced AWS / Kubernetes DevOps specialist.",
                apply_url="https://skill.jobs/job/therap-devops",
                source_reliability="verified_partner"
            ),
            NormalizedJob(
                id="chakri-802",
                source="Chakri",
                title="React Native Mobile Developer",
                company=CompanyInfo(name="Sheba.xyz", tier="Startup", verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                location="Banani, Dhaka",
                publish_date=now - timedelta(days=1),
                deadline=now + timedelta(days=10),
                experience=ExperienceRequirement(min_years=2.0, max_years=5.0, raw_text="2 to 5 years"),
                salary=SalaryInfo(disclosed=True, min_salary=75000, max_salary=100000, raw_text="Tk. 75,000 - 100,000", salary_bdt_min=900000, salary_bdt_max=1200000, salary_usd_min=7500, salary_usd_max=10000),
                job_context="Build cross-platform applications using React Native and Redux.",
                apply_url="https://chakri.com/job/sheba-react-native",
                source_reliability="verified_partner"
            )
        ],
        1: [  # Accounting/Finance
            NormalizedJob(
                id="skilljobs-101",
                source="Skill.jobs",
                title="Finance & Accounts Manager",
                company=CompanyInfo(name="Square Group", tier="Conglomerate", verified=True),
                category_id=1,
                category_name="Accounting/Finance",
                location="Mohakhali, Dhaka",
                publish_date=now - timedelta(days=1),
                deadline=now + timedelta(days=20),
                experience=ExperienceRequirement(min_years=5.0, max_years=8.0, raw_text="5 to 8 years"),
                salary=SalaryInfo(disclosed=True, min_salary=85000, max_salary=120000, raw_text="Tk. 85,000 - 120,000", salary_bdt_min=1020000, salary_bdt_max=1440000, salary_usd_min=8500, salary_usd_max=12000),
                job_context="Oversee financial reporting, NBR tax filings, and budgeting.",
                apply_url="https://skill.jobs/job/square-finance",
                source_reliability="verified_partner"
            ),
            NormalizedJob(
                id="chakri-102",
                source="Chakri",
                title="Senior Financial Planning & Analysis Analyst",
                company=CompanyInfo(name="bKash Limited", tier="MNC", verified=True),
                category_id=1,
                category_name="Accounting/Finance",
                location="Dhaka",
                publish_date=now - timedelta(days=2),
                deadline=now + timedelta(days=18),
                experience=ExperienceRequirement(min_years=3.0, max_years=6.0, raw_text="3 to 6 years"),
                salary=SalaryInfo(disclosed=True, min_salary=75000, max_salary=105000, raw_text="Tk. 75,000 - 105,000", salary_bdt_min=900000, salary_bdt_max=1260000, salary_usd_min=7500, salary_usd_max=10500),
                job_context="Lead quarterly forecasting, P&L reporting and revenue intelligence.",
                apply_url="https://chakri.com/job/bkash-fpa",
                source_reliability="verified_partner"
            )
        ],
        11: [  # Healthcare/Medical
            NormalizedJob(
                id="skilljobs-1101",
                source="Skill.jobs",
                title="Clinical Research & Medical Affairs Associate",
                company=CompanyInfo(name="Square Pharmaceuticals Ltd.", tier="Conglomerate", verified=True),
                category_id=11,
                category_name="Healthcare/Medical",
                location="Uttara, Dhaka",
                publish_date=now - timedelta(days=1),
                deadline=now + timedelta(days=22),
                experience=ExperienceRequirement(min_years=2.0, max_years=5.0, raw_text="2 to 5 years"),
                salary=SalaryInfo(disclosed=True, min_salary=55000, max_salary=80000, raw_text="Tk. 55,000 - 80,000", salary_bdt_min=660000, salary_bdt_max=960000, salary_usd_min=5500, salary_usd_max=8000),
                job_context="Design medical documentation, clinical trial oversight, and regulatory liaisons.",
                apply_url="https://skill.jobs/job/square-clinical-associate",
                source_reliability="verified_partner"
            ),
            NormalizedJob(
                id="chakri-1102",
                source="Chakri",
                title="Senior Medical Officer - Critical Care (ICU)",
                company=CompanyInfo(name="Evercare Hospital Dhaka", tier="MNC", verified=True),
                category_id=11,
                category_name="Healthcare/Medical",
                location="Bashundhara, Dhaka",
                publish_date=now - timedelta(days=2),
                deadline=now + timedelta(days=16),
                experience=ExperienceRequirement(min_years=3.0, max_years=6.0, raw_text="3 to 6 years"),
                salary=SalaryInfo(disclosed=True, min_salary=85000, max_salary=120000, raw_text="Tk. 85,000 - 120,000", salary_bdt_min=1020000, salary_bdt_max=1440000, salary_usd_min=8500, salary_usd_max=12000),
                job_context="Manage inpatient critical care admissions and multi-specialty triage in JCI-accredited facility.",
                apply_url="https://chakri.com/job/evercare-icu-smo",
                source_reliability="verified_partner"
            )
        ],
        63: [  # Nurse
            NormalizedJob(
                id="skilljobs-6301",
                source="Skill.jobs",
                title="Senior Staff Nurse - ICU / CCU",
                company=CompanyInfo(name="United Hospital Dhaka", tier="Corporate", verified=True),
                category_id=63,
                category_name="Nurse",
                category_type="Special Skilled",
                location="Gulshan-2, Dhaka",
                publish_date=now - timedelta(days=1),
                deadline=now + timedelta(days=15),
                experience=ExperienceRequirement(min_years=2.0, max_years=5.0, raw_text="2 to 5 years"),
                salary=SalaryInfo(disclosed=True, min_salary=45000, max_salary=65000, raw_text="Tk. 45,000 - 65,000", salary_bdt_min=540000, salary_bdt_max=780000, salary_usd_min=4500, salary_usd_max=6500),
                job_context="Deliver critical patient care, medication management and ventilation protocol tracking.",
                apply_url="https://skill.jobs/job/united-hospital-nurse",
                source_reliability="verified_partner"
            ),
            NormalizedJob(
                id="chakri-6302",
                source="Chakri",
                title="Specialized OT Registered Nurse",
                company=CompanyInfo(name="Square Hospital", tier="Corporate", verified=True),
                category_id=63,
                category_name="Nurse",
                category_type="Special Skilled",
                location="Panthapath, Dhaka",
                publish_date=now - timedelta(days=2),
                deadline=now + timedelta(days=18),
                experience=ExperienceRequirement(min_years=3.0, max_years=6.0, raw_text="3 to 6 years"),
                salary=SalaryInfo(disclosed=True, min_salary=50000, max_salary=70000, raw_text="Tk. 50,000 - 70,000", salary_bdt_min=600000, salary_bdt_max=840000, salary_usd_min=5000, salary_usd_max=7000),
                job_context="Surgical team collaboration, sterilization protocol enforcement and post-op care.",
                apply_url="https://chakri.com/job/square-hospital-ot-nurse",
                source_reliability="verified_partner"
            )
        ],
        9: [  # Marketing/Sales
            NormalizedJob(
                id="skilljobs-901",
                source="Skill.jobs",
                title="Brand & Digital Marketing Manager",
                company=CompanyInfo(name="Unilever Bangladesh", tier="MNC", verified=True),
                category_id=9,
                category_name="Marketing/Sales",
                location="Dhaka",
                publish_date=now - timedelta(days=1),
                deadline=now + timedelta(days=24),
                experience=ExperienceRequirement(min_years=4.0, max_years=7.0, raw_text="4 to 7 years"),
                salary=SalaryInfo(disclosed=True, min_salary=90000, max_salary=130000, raw_text="Tk. 90,000 - 130,000", salary_bdt_min=1080000, salary_bdt_max=1560000, salary_usd_min=9000, salary_usd_max=13000),
                job_context="Spearhead brand campaign strategies, multi-channel customer acquisition and ROI tracking.",
                apply_url="https://skill.jobs/job/unilever-brand-manager",
                source_reliability="verified_partner"
            ),
            NormalizedJob(
                id="chakri-902",
                source="Chakri",
                title="Enterprise Key Account Manager",
                company=CompanyInfo(name="Grameenphone Ltd.", tier="MNC", verified=True),
                category_id=9,
                category_name="Marketing/Sales",
                location="Bashundhara, Dhaka",
                publish_date=now - timedelta(days=2),
                deadline=now + timedelta(days=20),
                experience=ExperienceRequirement(min_years=3.0, max_years=6.0, raw_text="3 to 6 years"),
                salary=SalaryInfo(disclosed=True, min_salary=85000, max_salary=115000, raw_text="Tk. 85,000 - 115,000", salary_bdt_min=1020000, salary_bdt_max=1380000, salary_usd_min=8500, salary_usd_max=11500),
                job_context="Drive enterprise telecommunications contract acquisitions and B2B client success.",
                apply_url="https://chakri.com/job/gp-key-account-manager",
                source_reliability="verified_partner"
            )
        ],
        5: [  # Engineer/Architect
            NormalizedJob(
                id="skilljobs-501",
                source="Skill.jobs",
                title="Senior Mechanical Design Engineer",
                company=CompanyInfo(name="Walton Hi-Tech Industries PLC", tier="Conglomerate", verified=True),
                category_id=5,
                category_name="Engineer/Architect",
                location="Gazipur, Dhaka",
                publish_date=now - timedelta(days=2),
                deadline=now + timedelta(days=20),
                experience=ExperienceRequirement(min_years=3.0, max_years=7.0, raw_text="3 to 7 years"),
                salary=SalaryInfo(disclosed=True, min_salary=60000, max_salary=85000, raw_text="Tk. 60,000 - 85,000", salary_bdt_min=720000, salary_bdt_max=1020000, salary_usd_min=6000, salary_usd_max=8500),
                job_context="Lead mechanical component modeling, CAD structural stress testing and production deployment.",
                apply_url="https://skill.jobs/job/walton-mechanical-engineer",
                source_reliability="verified_partner"
            ),
            NormalizedJob(
                id="chakri-502",
                source="Chakri",
                title="Senior Project Architect",
                company=CompanyInfo(name="Shanta Holdings", tier="Corporate", verified=True),
                category_id=5,
                category_name="Engineer/Architect",
                location="Tejgaon, Dhaka",
                publish_date=now - timedelta(days=1),
                deadline=now + timedelta(days=25),
                experience=ExperienceRequirement(min_years=5.0, max_years=9.0, raw_text="5 to 9 years"),
                salary=SalaryInfo(disclosed=True, min_salary=95000, max_salary=140000, raw_text="Tk. 95,000 - 140,000", salary_bdt_min=1140000, salary_bdt_max=1680000, salary_usd_min=9500, salary_usd_max=14000),
                job_context="Oversee high-rise residential and commercial architectural blueprints and construction fidelity.",
                apply_url="https://chakri.com/job/shanta-senior-architect",
                source_reliability="verified_partner"
            )
        ]
    }

def fetch_sample_partner_jobs(category_id: int, category_name: str) -> List[NormalizedJob]:
    """
    Simulated public feed connectors for portals like Skill.jobs and Chakri.com
    providing cross-platform aggregation demonstration for a given category.
    """
    registry = get_partner_job_registry()
    return registry.get(category_id, [])

def fetch_all_partner_jobs() -> List[NormalizedJob]:
    """
    Retrieve all partner portal openings across all categories.
    """
    registry = get_partner_job_registry()
    all_jobs = []
    for cat_jobs in registry.values():
        all_jobs.extend(cat_jobs)
    return all_jobs
