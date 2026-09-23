import re
from datetime import datetime, timezone
from typing import Optional, Tuple, List, Dict
from core.models import (
    SalaryInfo, ExperienceRequirement, CompanyTier, 
    WorkplaceType, RemotePolicy, RemoteEligibility, CandidateEligibility,
    ExperienceLevel, EmploymentType
)

# Currency exchange rates relative to USD (1 USD = X Currency)
EXCHANGE_RATES_TO_USD = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.28,
    "BDT": 1 / 120.0,   # ~120 BDT per USD
    "INR": 1 / 84.0,    # ~84 INR per USD
    "SGD": 0.76,
    "AED": 0.272,
    "CAD": 0.74,
    "AUD": 0.66,
    "JPY": 0.0067,
    "CHF": 1.14
}

COUNTRY_REGIONS = {
    "Bangladesh": "Asia-Pacific",
    "India": "Asia-Pacific",
    "China": "Asia-Pacific",
    "Japan": "Asia-Pacific",
    "South Korea": "Asia-Pacific",
    "Singapore": "Asia-Pacific",
    "Malaysia": "Asia-Pacific",
    "Australia": "Oceania",
    "New Zealand": "Oceania",
    "United States": "North America",
    "Canada": "North America",
    "United Kingdom": "Europe",
    "Germany": "Europe",
    "France": "Europe",
    "Netherlands": "Europe",
    "Ireland": "Europe",
    "Sweden": "Europe",
    "Switzerland": "Europe",
    "United Arab Emirates": "Middle East",
    "Saudi Arabia": "Middle East",
    "Qatar": "Middle East"
}

TOP_MNCS = {
    "unilever", "british american tobacco", "bat", "grameenphone", "gp", 
    "robi", "banglalink", "nestle", "standard chartered", "hsbc", "huawei", 
    "samsung", "chevron", "marico", "reckitt", "ericsson", "novartis", "sanofi",
    "google", "microsoft", "amazon", "apple", "meta", "netflix", "stripe", "uber"
}

TOP_CONGLOMERATES_AND_BANKS = {
    "brac", "brac bank", "bkash", "eastern bank", "ebl", "city bank", 
    "dutch-bangla", "dbbl", "idlc", "ipdc", "pubali bank", "mutual trust bank",
    "square", "square pharmaceuticals", "beximco", "pran", "rfl", "pran-rfl",
    "aci", "akij", "walton", "meghna group", "mgi", "bashundhara", "apex", 
    "dbl", "summit", "ananta", "brain station 23", "enosis", "optimizely", 
    "pathao", "chaldal", "daraz", "icddr,b", "tcs", "infosys", "wipro", "reliance"
}

def convert_to_usd(amount: float, from_curr: str) -> float:
    rate = EXCHANGE_RATES_TO_USD.get(from_curr.upper(), 1.0)
    return round(amount * rate, 2)

def convert_usd_to_bdt(usd_amount: float) -> float:
    return round(usd_amount * 120.0, 2)

def parse_salary(raw_salary: Optional[str], default_currency: str = "BDT") -> SalaryInfo:
    """Parse global multi-currency salary strings into structured SalaryInfo."""
    if not raw_salary:
        return SalaryInfo(disclosed=False, raw_text="Negotiable", salary_type="not_disclosed")
    
    clean_text = raw_salary.strip()
    lower = clean_text.lower()
    
    if any(k in lower for k in ["negotiable", "attractive", "company policy", "not disclosed", "confidential", "competitive"]):
        return SalaryInfo(disclosed=False, raw_text=clean_text, salary_type="not_disclosed")
    
    # Detect currency symbol
    currency = default_currency
    if "$" in clean_text or "usd" in lower:
        currency = "USD"
    elif "€" in clean_text or "eur" in lower:
        currency = "EUR"
    elif "£" in clean_text or "gbp" in lower:
        currency = "GBP"
    elif "₹" in clean_text or "inr" in lower or "lpa" in lower:
        currency = "INR"
    elif "tk" in lower or "bdt" in lower:
        currency = "BDT"
    elif "s$" in clean_text or "sgd" in lower:
        currency = "SGD"
    elif "aed" in lower:
        currency = "AED"
    
    # Handle "k" notation e.g. "$120k - $150k"
    k_pattern = re.findall(r'(\d+(?:\.\d+)?)\s*k\b', lower)
    if k_pattern:
        numbers = [float(n) * 1000 for n in k_pattern]
    else:
        # Handle Indian Lakhs e.g. "12 - 18 LPA"
        lakh_pattern = re.findall(r'(\d+(?:\.\d+)?)\s*(?:lpa|lakh|lac)', lower)
        if lakh_pattern:
            numbers = [float(n) * 100000 for n in lakh_pattern]
            currency = "INR"
        else:
            normalized = clean_text.replace(",", "")
            numbers = [float(n) for n in re.findall(r'\b\d{3,8}\b', normalized)]
    
    if not numbers:
        return SalaryInfo(disclosed=False, raw_text=clean_text, salary_type="not_disclosed")
    
    if len(numbers) >= 2:
        min_sal = min(numbers[0], numbers[1])
        max_sal = max(numbers[0], numbers[1])
    else:
        min_sal = numbers[0]
        max_sal = numbers[0]
        
    period = "Monthly"
    if "year" in lower or "annual" in lower or "lpa" in lower or (currency in ["USD", "EUR", "GBP", "CAD", "AUD"] and min_sal >= 20000):
        period = "Annual"
    
    # Convert to annual for USD/BDT equivalents if monthly
    annual_min = min_sal * 12 if period == "Monthly" and currency in ["BDT", "INR"] else min_sal
    annual_max = max_sal * 12 if period == "Monthly" and currency in ["BDT", "INR"] else max_sal
    
    usd_min = convert_to_usd(annual_min, currency)
    usd_max = convert_to_usd(annual_max, currency)
    bdt_min = convert_usd_to_bdt(usd_min)
    bdt_max = convert_usd_to_bdt(usd_max)
    
    return SalaryInfo(
        disclosed=True,
        min_salary=min_sal,
        max_salary=max_sal,
        currency=currency,
        period=period,
        raw_text=clean_text,
        salary_type="employer_provided",
        salary_usd_min=usd_min,
        salary_usd_max=usd_max,
        salary_bdt_min=bdt_min,
        salary_bdt_max=bdt_max
    )

def parse_experience(raw_exp: Optional[str]) -> ExperienceRequirement:
    """Parse experience text like '4 to 8 years' or 'At least 2 year(s)'."""
    if not raw_exp:
        return ExperienceRequirement(min_years=0.0, max_years=None, raw_text="")
    
    clean = raw_exp.strip()
    lower = clean.lower()
    
    if "fresher" in lower or "entry" in lower or "graduate" in lower:
        return ExperienceRequirement(min_years=0.0, max_years=1.0, raw_text=clean)
    if "intern" in lower:
        return ExperienceRequirement(min_years=0.0, max_years=1.0, raw_text=clean)
        
    numbers = [float(n) for n in re.findall(r'\b\d+(?:\.\d+)?\b', clean)]
    if not numbers:
        return ExperienceRequirement(min_years=0.0, max_years=None, raw_text=clean)
        
    if len(numbers) >= 2 and ("to" in lower or "-" in lower):
        min_y = min(numbers[0], numbers[1])
        max_y = max(numbers[0], numbers[1])
    elif "at least" in lower or "+" in lower or "minimum" in lower:
        min_y = numbers[0]
        max_y = None
    elif "at most" in lower or "maximum" in lower:
        min_y = 0.0
        max_y = numbers[0]
    else:
        min_y = numbers[0]
        max_y = numbers[0]
        
    return ExperienceRequirement(min_years=min_y, max_years=max_y, raw_text=clean)

def classify_experience_level(exp: ExperienceRequirement) -> ExperienceLevel:
    """Categorize experience requirement into career level."""
    raw = (exp.raw_text or "").lower()
    if "intern" in raw:
        return "Internship"
    if "fresher" in raw or "entry" in raw or "graduate" in raw:
        return "Entry Level"
        
    min_y = exp.min_years if exp.min_years is not None else 0.0
    if min_y < 1.0:
        return "Entry Level"
    elif min_y <= 2.0:
        return "Junior"
    elif min_y <= 5.0:
        return "Mid Level"
    elif min_y <= 9.0:
        return "Senior"
    else:
        return "Lead / Principal"

def normalize_location(location_str: Optional[str]) -> Tuple[str, str, str]:
    """Extract (city, country, region) from location string."""
    if not location_str:
        return "Dhaka", "Bangladesh", "Asia-Pacific"
        
    loc = location_str.strip()
    lower = loc.lower()
    
    country_mappings = [
        ("bangladesh", "Bangladesh"), ("dhaka", "Bangladesh"), ("chittagong", "Bangladesh"), ("sylhet", "Bangladesh"),
        ("india", "India"), ("bangalore", "India"), ("bengaluru", "India"), ("delhi", "India"), ("mumbai", "India"), ("hyderabad", "India"),
        ("united states", "United States"), ("usa", "United States"), ("us", "United States"), ("new york", "United States"), ("san francisco", "United States"), ("seattle", "United States"), ("austin", "United States"),
        ("united kingdom", "United Kingdom"), ("uk", "United Kingdom"), ("london", "United Kingdom"),
        ("germany", "Germany"), ("berlin", "Germany"), ("munich", "Germany"), ("frankfurt", "Germany"),
        ("singapore", "Singapore"),
        ("japan", "Japan"), ("tokyo", "Japan"),
        ("canada", "Canada"), ("toronto", "Canada"), ("vancouver", "Canada"),
        ("australia", "Australia"), ("sydney", "Australia"), ("melbourne", "Australia"),
        ("uae", "United Arab Emirates"), ("dubai", "United Arab Emirates"), ("abu dhabi", "United Arab Emirates"),
        ("china", "China"), ("beijing", "China"), ("shanghai", "China"), ("shenzhen", "China"),
        ("netherlands", "Netherlands"), ("amsterdam", "Netherlands"),
        ("ireland", "Ireland"), ("dublin", "Ireland"),
        ("france", "France"), ("paris", "France"),
        ("sweden", "Sweden"), ("stockholm", "Sweden"),
        ("switzerland", "Switzerland"), ("zurich", "Switzerland"),
        ("qatar", "Qatar"), ("doha", "Qatar"),
        ("saudi arabia", "Saudi Arabia"), ("riyadh", "Saudi Arabia")
    ]
    
    detected_country = "Bangladesh"
    for pattern, c_name in country_mappings:
        if re.search(r'\b' + re.escape(pattern) + r'\b', lower):
            detected_country = c_name
            break
            
    region = COUNTRY_REGIONS.get(detected_country, "Worldwide")
    city = loc.split(",")[0].strip() if "," in loc else loc
    return city, detected_country, region

def classify_remote_policy(title: str, location: str, context: str = "") -> Tuple[WorkplaceType, RemoteEligibility]:
    """Intelligently classify workplace mode and candidate remote eligibility."""
    combined = f"{title} {location} {context}".lower()
    
    # 1. Check for explicit Worldwide / Anywhere Remote
    is_worldwide = any(p in combined for p in [
        "worldwide remote", "remote - worldwide", "work from anywhere", 
        "remote: anywhere", "anywhere in the world", "global remote", 
        "remote worldwide", "100% remote (worldwide)"
    ])
    
    # 2. Check for Country-Restricted Remote
    restricted_countries = []
    if "remote - us only" in combined or "us only" in combined or "remote (us)" in combined or "remote (usa)" in combined:
        restricted_countries.append("United States")
    if "remote - india only" in combined or "remote (india)" in combined or "india only" in combined:
        restricted_countries.append("India")
    if "remote - uk only" in combined or "uk only" in combined:
        restricted_countries.append("United Kingdom")
    if "remote - germany only" in combined or "germany only" in combined:
        restricted_countries.append("Germany")
    if "bangladesh only" in combined:
        restricted_countries.append("Bangladesh")
        
    # 3. Check for Regional Remote
    restricted_regions = []
    if "apac" in combined or "asia-pacific" in combined or "remote - asia" in combined:
        restricted_regions.append("Asia-Pacific")
    if "emea" in combined or "europe" in combined or "remote - europe" in combined:
        restricted_regions.append("Europe")
    if "americas" in combined or "latam" in combined:
        restricted_regions.append("Americas")
        
    # 4. Visa Sponsorship & International applicants
    visa_sponsorship = any(v in combined for v in [
        "visa sponsorship", "visa sponsored", "sponsorship available", "relocation assistance", 
        "visa support", "willing to sponsor"
    ])
    work_auth_required = any(w in combined for w in [
        "must be authorized to work", "no sponsorship", "valid work authorization", "citizens only"
    ])
    accepts_international = is_worldwide or visa_sponsorship or ("international applicants" in combined)

    # 5. Workplace Type
    if is_worldwide or restricted_countries or restricted_regions or "remote" in combined:
        if "hybrid" in combined:
            workplace_type = "Hybrid"
            policy = "Country-Restricted" if restricted_countries else ("Regional" if restricted_regions else "Worldwide")
        else:
            workplace_type = "Remote"
            policy = "Worldwide" if is_worldwide else ("Country-Restricted" if restricted_countries else ("Regional" if restricted_regions else "Worldwide"))
    elif "hybrid" in combined:
        workplace_type = "Hybrid"
        policy = "Country-Restricted"
    else:
        workplace_type = "On-site"
        policy = "Not Remote"

    eligibility = RemoteEligibility(
        policy=policy,
        allowed_countries=restricted_countries,
        allowed_regions=restricted_regions,
        timezone_requirements="Any" if is_worldwide else None,
        accepts_international=accepts_international,
        requires_work_authorization=work_auth_required,
        visa_sponsorship=visa_sponsorship,
        relocation_assistance="relocation" in combined
    )
    
    return workplace_type, eligibility

def evaluate_candidate_eligibility(
    job_country: str,
    workplace_type: WorkplaceType,
    remote_eligibility: RemoteEligibility,
    candidate_origin_country: str = "Bangladesh"
) -> CandidateEligibility:
    """Evaluate whether an applicant from candidate_origin_country can realistically apply."""
    origin = candidate_origin_country.strip().title()
    origin_region = COUNTRY_REGIONS.get(origin, "Asia-Pacific")
    
    # On-site / Hybrid in same country
    if workplace_type in ["On-site", "Hybrid"] and job_country.lower() == origin.lower():
        return CandidateEligibility(
            is_eligible=True,
            status="eligible",
            reason=f"Local {workplace_type.lower()} position in {job_country}."
        )
        
    # Remote Worldwide
    if workplace_type == "Remote" and (remote_eligibility.policy == "Worldwide" or remote_eligibility.accepts_international):
        return CandidateEligibility(
            is_eligible=True,
            status="eligible",
            reason=f"Worldwide remote opportunity. Applicants from {origin} are fully eligible."
        )
        
    # Country-restricted remote
    if remote_eligibility.allowed_countries:
        allowed = [c.lower() for c in remote_eligibility.allowed_countries]
        if origin.lower() in allowed:
            return CandidateEligibility(
                is_eligible=True,
                status="eligible",
                reason=f"Remote position authorized for residents of {origin}."
            )
        else:
            country_str = ", ".join(remote_eligibility.allowed_countries)
            return CandidateEligibility(
                is_eligible=False,
                status="ineligible",
                reason=f"Position is restricted to applicants residing in {country_str}. Applicants from {origin} are not eligible."
            )
            
    # Regional Remote
    if remote_eligibility.allowed_regions:
        if origin_region in remote_eligibility.allowed_regions:
            return CandidateEligibility(
                is_eligible=True,
                status="eligible",
                reason=f"Regional remote ({', '.join(remote_eligibility.allowed_regions)}) — covers {origin}."
            )
        else:
            region_str = ", ".join(remote_eligibility.allowed_regions)
            return CandidateEligibility(
                is_eligible=False,
                status="ineligible",
                reason=f"Restricted to {region_str} timezone/region. {origin} is outside this region."
            )
            
    # On-site abroad with Visa Sponsorship
    if job_country.lower() != origin.lower() and remote_eligibility.visa_sponsorship:
        return CandidateEligibility(
            is_eligible=True,
            status="eligible",
            reason=f"International position in {job_country} with Visa Sponsorship available."
        )
        
    # On-site abroad without sponsorship
    if job_country.lower() != origin.lower() and workplace_type in ["On-site", "Hybrid"]:
        return CandidateEligibility(
            is_eligible=False,
            status="conditional",
            reason=f"Located in {job_country}. Requires existing work authorization or permanent residency."
        )

    return CandidateEligibility(
        is_eligible=True,
        status="eligible",
        reason="General opportunity — open to qualified candidates."
    )

def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse various ISO and textual date formats."""
    if not date_str:
        return None
    date_str = date_str.strip()
    
    for fmt in [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%b %d, %Y",
        "%d %b %Y"
    ]:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
            
    m = re.search(r'([A-Za-z]{3})\s+(\d{1,2}),\s+(\d{4})', date_str)
    if m:
        try:
            month_str, day_str, year_str = m.groups()
            return datetime.strptime(f"{month_str} {day_str} {year_str}", "%b %d %Y").replace(tzinfo=timezone.utc)
        except Exception:
            pass

    return None

def classify_company_tier(company_name: str) -> CompanyTier:
    """Classify corporate standing based on company name."""
    lower = company_name.lower().strip()
    
    if any(c in lower for c in ["leading", "reputed", "confidential", "multinational company", "group of companies"]) and len(lower.split()) <= 5:
        if not any(top in lower for top in TOP_CONGLOMERATES_AND_BANKS):
            return "Confidential"
            
    for mnc in TOP_MNCS:
        if mnc in lower:
            return "MNC"
            
    for cong in TOP_CONGLOMERATES_AND_BANKS:
        if cong in lower:
            if "bank" in lower or "financial" in lower or "ipdc" in lower or "idlc" in lower:
                return "Financial Institution"
            return "Conglomerate"
            
    if any(k in lower for k in ["ltd", "limited", "plc", "corp", "group", "holdings", "inc", "gmbh", "technologies"]):
        return "Corporate"
        
    return "SME"

def clean_html(raw_html: str) -> str:
    """Remove HTML tags and entities from job context."""
    if not raw_html:
        return ""
    text = re.sub(r'<[^>]+>', ' ', raw_html)
    text = text.replace("&amp;", "&").replace("&nbsp;", " ").replace("&quot;", '"').replace("&#39;", "'")
    return re.sub(r'\s+', ' ', text).strip()
