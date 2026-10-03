from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime

JobSource = str
CompanyTier = Literal["MNC", "Conglomerate", "Financial Institution", "Corporate", "SME", "Startup", "Confidential"]
WorkplaceType = Literal["Remote", "Hybrid", "On-site"]
RemotePolicy = Literal["Worldwide", "Regional", "Country-Restricted", "Not Remote"]
ExperienceLevel = Literal["Internship", "Entry Level", "Junior", "Mid Level", "Senior", "Lead / Principal", "Executive"]
EmploymentType = Literal["Full-time", "Part-time", "Contract", "Freelance", "Internship"]
SourceReliability = Literal["official_career_page", "verified_partner", "major_board", "third_party", "agency"]

class RemoteEligibility(BaseModel):
    policy: RemotePolicy = "Not Remote"
    allowed_countries: List[str] = Field(default_factory=list)
    allowed_regions: List[str] = Field(default_factory=list)
    timezone_requirements: Optional[str] = None
    accepts_international: bool = False
    requires_work_authorization: bool = False
    visa_sponsorship: bool = False
    relocation_assistance: bool = False

class CandidateEligibility(BaseModel):
    is_eligible: bool = True
    status: Literal["eligible", "ineligible", "conditional"] = "eligible"
    reason: str = "Candidate meets geographic and remote requirements"

class SalaryInfo(BaseModel):
    disclosed: bool = False
    min_salary: Optional[float] = None
    max_salary: Optional[float] = None
    currency: str = "BDT"
    period: str = "Monthly"
    raw_text: str = "Negotiable"
    salary_type: Literal["employer_provided", "estimated", "not_disclosed"] = "not_disclosed"
    salary_usd_min: Optional[float] = None
    salary_usd_max: Optional[float] = None
    salary_bdt_min: Optional[float] = None
    salary_bdt_max: Optional[float] = None

class ExperienceRequirement(BaseModel):
    min_years: Optional[float] = 0.0
    max_years: Optional[float] = None
    raw_text: str = ""

class CompanyInfo(BaseModel):
    name: str
    tier: CompanyTier = "Corporate"
    verified: bool = False
    logo_url: Optional[str] = None
    website: Optional[str] = None

class NormalizedJob(BaseModel):
    id: str
    source: JobSource = "BDJobs"
    source_type: str = "GLOBAL_JOB_BOARD"
    source_job_id: Optional[str] = None
    title: str
    company: CompanyInfo
    category_id: int = 8
    category_name: str = "IT/Telecommunication"
    category_type: str = "Functional"
    country: str = "Bangladesh"
    city: Optional[str] = "Dhaka"
    location: str = "Dhaka"
    region: str = "Worldwide"
    workplace_type: WorkplaceType = "On-site"
    remote_type: str = "ONSITE"  # REMOTE, HYBRID, ONSITE, UNKNOWN
    remote_eligibility: RemoteEligibility = Field(default_factory=RemoteEligibility)
    candidate_eligibility: CandidateEligibility = Field(default_factory=CandidateEligibility)
    publish_date: Optional[datetime] = None  # posted_at
    deadline: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    collected_at: Optional[datetime] = None
    experience: ExperienceRequirement = Field(default_factory=ExperienceRequirement)
    experience_level: ExperienceLevel = "Mid Level"
    salary: SalaryInfo = Field(default_factory=SalaryInfo)
    job_type: str = "FullTime"
    employment_type: EmploymentType = "Full-time"
    vacancies: int = 1
    skills_required: List[str] = Field(default_factory=list)
    job_context: str = ""  # description
    apply_url: str
    source_reliability: SourceReliability = "major_board"
    canonical_id: Optional[str] = None
    alternate_sources: List[str] = Field(default_factory=list)

    @property
    def posted_at(self) -> Optional[datetime]:
        return self.publish_date

    @property
    def description(self) -> str:
        return self.job_context

    @property
    def salary_min(self) -> Optional[float]:
        return self.salary.min_salary

    @property
    def salary_max(self) -> Optional[float]:
        return self.salary.max_salary

    @property
    def salary_currency(self) -> str:
        return self.salary.currency

    @property
    def skills(self) -> List[str]:
        return self.skills_required

    def to_unified_dict(self) -> Dict[str, Any]:
        """Returns job formatted exactly to Section 8 Unified Job Schema."""
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company.name if self.company else "",
            "location": self.location,
            "country": self.country,
            "region": self.region,
            "remote_type": self.remote_type,
            "employment_type": self.employment_type,
            "experience_level": self.experience_level,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "salary_currency": self.salary_currency,
            "skills": self.skills,
            "description": self.description,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "application_url": self.apply_url,
            "source": self.source,
            "source_job_id": self.source_job_id or self.id,
            "source_type": self.source_type,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None
        }

class UserProfile(BaseModel):
    target_category_ids: List[int] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experience_years: float = 2.0
    expected_salary: Optional[float] = None
    preferred_job_type: Optional[str] = "FullTime"
    preferred_locations: List[str] = Field(default_factory=list)
    candidate_origin_country: str = "Bangladesh"
    preferred_countries: List[str] = Field(default_factory=list)
    preferred_workplace_type: List[str] = Field(default_factory=lambda: ["Remote", "Hybrid", "On-site"])
    requires_visa_sponsorship: bool = False
    education_level: Optional[str] = None
    desired_roles: List[str] = Field(default_factory=list)

class ScoringWeights(BaseModel):
    w_recency: float = 0.20
    w_salary: float = 0.30
    w_profile: float = 0.35
    w_employer: float = 0.15

class ScoreBreakdown(BaseModel):
    recency_score: float
    salary_score: float
    profile_match_score: float
    employer_score: float
    final_score: float
    explanation: str

class ScoredJob(BaseModel):
    job: NormalizedJob
    score: ScoreBreakdown
