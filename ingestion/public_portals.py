from typing import List
from datetime import datetime, timezone, timedelta
from core.models import NormalizedJob, CompanyInfo, SalaryInfo, ExperienceRequirement

def fetch_sample_partner_jobs(category_id: int, category_name: str) -> List[NormalizedJob]:
    """
    Simulated public feed connectors for portals like Skill.jobs and Chakri.com
    providing cross-platform aggregation demonstration.
    """
    now = datetime.now(timezone.utc)
    
    mock_registry = {
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
                salary=SalaryInfo(disclosed=True, min_salary=110000, max_salary=150000, raw_text="Tk. 110,000 - 150,000"),
                job_context="Looking for an experienced AWS / Kubernetes DevOps specialist.",
                apply_url="https://skill.jobs/job/therap-devops"
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
                salary=SalaryInfo(disclosed=True, min_salary=75000, max_salary=100000, raw_text="Tk. 75,000 - 100,000"),
                job_context="Build cross-platform applications using React Native and Redux.",
                apply_url="https://chakri.com/job/sheba-react-native"
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
                salary=SalaryInfo(disclosed=True, min_salary=85000, max_salary=120000, raw_text="Tk. 85,000 - 120,000"),
                job_context="Oversee financial reporting, NBR tax filings, and budgeting.",
                apply_url="https://skill.jobs/job/square-finance"
            )
        ]
    }
    
    return mock_registry.get(category_id, [])
