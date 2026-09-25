import re
import uuid
from typing import Optional
from datetime import datetime, timezone, timedelta
from core.models import NormalizedJob, CompanyInfo, WorkplaceType, RemoteEligibility
from core.normalizer import parse_salary, parse_experience, classify_company_tier

def parse_pasted_facebook_text(text: str, target_category_id: int = 8, category_name: str = "IT/Telecommunication") -> Optional[NormalizedJob]:
    """
    ToS-Compliant Facebook Ingestion:
    Parses unstructured text copied from Facebook Groups, Pages, or posts into a NormalizedJob.
    Does NOT use automated scrapers or crawlers (violates Facebook ToS).
    Supports manual text pasting and official Graph API payloads.
    """
    if not text or len(text.strip()) < 15:
        return None

    clean_text = text.strip()
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    if not lines:
        return None

    title = ""
    company_name = "Company on Facebook"
    location = "Dhaka, Bangladesh"
    apply_url = "https://www.facebook.com"
    workplace_type = "On-site"
    remote_policy = "Not Remote"

    # 1. Detect apply email or link in text
    url_match = re.search(r'https?://[^\s]+', clean_text)
    if url_match:
        apply_url = url_match.group(0).rstrip('.,;()[]')
    else:
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', clean_text)
        if email_match:
            apply_url = f"mailto:{email_match.group(0)}"

    # 2. Detect Remote / Hybrid / On-site
    lower_text = clean_text.lower()
    if "remote" in lower_text:
        workplace_type = "Remote"
        remote_policy = "Worldwide" if ("worldwide" in lower_text or "anywhere" in lower_text or "global" in lower_text) else "Regional"
    elif "hybrid" in lower_text:
        workplace_type = "Hybrid"
        remote_policy = "Not Remote"


    # 3. Extract Role / Title via regex patterns
    title_patterns = [
        r'(?:position|role|job\s*title|designation)\s*[:\-–]\s*([^\n\r]+)',
        r'(?:we\s+are\s+hiring|hiring|urgently\s+hiring|looking\s+for|we\s+need)\s*[:\-–]?\s*(?:a\s+|an\s+)?([A-Za-z0-9\s\+\#\/\.\-]+?(?:developer|engineer|lead|specialist|designer|manager|analyst|executive|officer|intern|architect|consultant))',
        r'^([A-Za-z0-9\s\+\#\/\.\-]+?(?:developer|engineer|lead|specialist|designer|manager|analyst|executive|officer|intern|architect))'
    ]
    for pat in title_patterns:
        m = re.search(pat, clean_text, re.IGNORECASE | re.MULTILINE)
        if m:
            candidate_title = m.group(1).strip().strip("!.,:;")
            if 3 < len(candidate_title) < 70:
                title = candidate_title
                break

    if not title:
        # Fallback to first line if reasonably short, else generic
        first_line = lines[0].strip("!.,:; ")
        if len(first_line) < 60 and not any(w in first_line.lower() for w in ["hiring", "urgent", "announcement", "opportunity"]):
            title = first_line
        else:
            title = "Job Opportunity (Facebook)"

    # 4. Extract Company Name
    company_patterns = [
        r'(?:company|organization|agency|firm)\s*[:\-–]\s*([^\n\r,]+)',
        r'(?:at|with)\s+([A-Z][A-Za-z0-9\s\.\&\-]{2,40})(?:\s+is\s+hiring|\s+located|\.|\n)',
        r'(?:welcome\s+to|team\s+at)\s+([A-Za-z0-9\s\.\&\-]{2,40})'
    ]
    for pat in company_patterns:
        m = re.search(pat, clean_text, re.IGNORECASE)
        if m:
            candidate_company = m.group(1).strip().strip("!.,:;")
            if len(candidate_company) < 50:
                company_name = candidate_company
                break

    # 5. Extract Location
    loc_match = re.search(r'(?:location|job\s*location|address)\s*[:\-–]\s*([^\n\r]+)', clean_text, re.IGNORECASE)
    if loc_match:
        location = loc_match.group(1).strip().strip("!.,;")
    elif "remote" in lower_text and "worldwide" in lower_text:
        location = "Remote (Worldwide)"
    elif "dhaka" in lower_text:
        location = "Dhaka, Bangladesh"
    elif "chittagong" in lower_text or "chattogram" in lower_text:
        location = "Chittagong, Bangladesh"

    # 6. Parse Experience & Salary
    exp_info = parse_experience(clean_text)
    sal_info = parse_salary(clean_text)

    # 7. Deadline estimation (default 14 days from now if not found)
    pub_date = datetime.now(timezone.utc)
    deadline = pub_date + timedelta(days=14)
    deadline_match = re.search(r'(?:deadline|last\s*date|apply\s*before)\s*[:\-–]?\s*([^\n\r]+)', clean_text, re.IGNORECASE)
    # Context summary
    job_context = clean_text[:1500]

    return NormalizedJob(
        id=f"fb-{uuid.uuid4().hex[:8]}",
        source="Facebook",
        title=title,
        company=CompanyInfo(
            name=company_name,
            tier=classify_company_tier(company_name),
            verified=False
        ),
        category_id=target_category_id,
        category_name=category_name,
        location=location,
        workplace_type=workplace_type,
        remote_eligibility=RemoteEligibility(
            policy=remote_policy,
            accepts_international="worldwide" in lower_text or "anywhere" in lower_text or "global" in lower_text
        ),
        publish_date=pub_date,
        deadline=deadline,
        experience=exp_info,
        salary=sal_info,
        job_type="FullTime",
        vacancies=1,
        job_context=job_context,
        apply_url=apply_url
    )
