import re
import json
import uuid
from typing import Optional, Dict
from datetime import datetime, timezone, timedelta
from core.models import NormalizedJob, CompanyInfo
from core.normalizer import parse_salary, parse_experience, classify_company_tier

def parse_pasted_linkedin_text(text: str, target_category_id: int = 8, category_name: str = "IT/Telecommunication") -> Optional[NormalizedJob]:
    """
    ToS-Compliant LinkedIn Ingestion:
    Parses unstructured text copied directly from a LinkedIn Job posting into a NormalizedJob.
    Does not make automated network requests to LinkedIn.
    """
    if not text or len(text.strip()) < 20:
        return None
        
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    if not lines:
        return None
        
    # Heuristic 1: Check for JSON-LD snippet first
    json_match = re.search(r'\{[^{}]*"@type"\s*:\s*"JobPosting"[^{}]*\}', text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            title = data.get('title', 'LinkedIn Job')
            company_raw = data.get('hiringOrganization', {})
            comp_name = company_raw.get('name', 'Company on LinkedIn') if isinstance(company_raw, dict) else str(company_raw)
            desc = data.get('description', '')
            
            return NormalizedJob(
                id=f"linkedin-{uuid.uuid4().hex[:8]}",
                source="LinkedIn",
                title=title,
                company=CompanyInfo(name=comp_name, tier=classify_company_tier(comp_name), verified=True),
                category_id=target_category_id,
                category_name=category_name,
                location=data.get('jobLocation', {}).get('address', {}).get('addressLocality', 'Dhaka, Bangladesh') if isinstance(data.get('jobLocation'), dict) else "Bangladesh",
                publish_date=datetime.now(timezone.utc),
                deadline=datetime.now(timezone.utc) + timedelta(days=21),
                experience=parse_experience(desc),
                salary=parse_salary(desc),
                job_context=desc[:1000],
                apply_url="https://www.linkedin.com/jobs/"
            )
        except Exception:
            pass

    # Heuristic 2: Standard LinkedIn Copy-Paste format
    # Line 0: Job Title (e.g., "Full Stack Developer")
    # Line 1: Company Name (e.g., "Brain Station 23")
    # Line 2: Location (e.g., "Dhaka, Bangladesh")
    title = lines[0]
    company_name = lines[1] if len(lines) > 1 else "Unknown Company"
    location = lines[2] if len(lines) > 2 else "Dhaka, Bangladesh"
    
    # If title has separator like "Full Stack Developer at Company"
    if " at " in title:
        parts = title.split(" at ")
        title = parts[0].strip()
        company_name = parts[1].strip()
    elif " · " in title:
        parts = title.split(" · ")
        title = parts[0].strip()
        company_name = parts[1].strip()

    body_text = " ".join(lines[3:]) if len(lines) > 3 else " ".join(lines)
    
    # Check recency hints
    pub_date = datetime.now(timezone.utc)
    if "day ago" in body_text or "days ago" in body_text:
        m = re.search(r'(\d+)\s+day', body_text)
        if m:
            pub_date = pub_date - timedelta(days=int(m.group(1)))
    elif "week ago" in body_text or "weeks ago" in body_text:
        m = re.search(r'(\d+)\s+week', body_text)
        if m:
            pub_date = pub_date - timedelta(days=int(m.group(1)) * 7)

    return NormalizedJob(
        id=f"linkedin-{uuid.uuid4().hex[:8]}",
        source="LinkedIn",
        title=title,
        company=CompanyInfo(
            name=company_name,
            tier=classify_company_tier(company_name),
            verified=True
        ),
        category_id=target_category_id,
        category_name=category_name,
        location=location,
        publish_date=pub_date,
        deadline=pub_date + timedelta(days=21),
        experience=parse_experience(body_text),
        salary=parse_salary(body_text),
        job_type="FullTime",
        vacancies=1,
        job_context=body_text[:1200],
        apply_url="https://www.linkedin.com/jobs/"
    )
