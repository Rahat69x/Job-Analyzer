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
    title: str
    company: CompanyInfo
    category_id: int = 8
    category_name: str = "IT/Telecommunication"
    category_type: str = "Functional"
    country: str = "Bangladesh"
    city: Optional[str] = "Dhaka"
    location: str = "Dhaka"
    workplace_type: WorkplaceType = "On-site"
    remote_eligibility: RemoteEligibility = Field(default_factory=RemoteEligibility)
    candidate_eligibility: CandidateEligibility = Field(default_factory=CandidateEligibility)
    publish_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    experience: ExperienceRequirement = Field(default_factory=ExperienceRequirement)
    experience_level: ExperienceLevel = "Mid Level"
    salary: SalaryInfo = Field(default_factory=SalaryInfo)
    job_type: str = "FullTime"
    employment_type: EmploymentType = "Full-time"
    vacancies: int = 1
    skills_required: List[str] = Field(default_factory=list)
    job_context: str = ""
    apply_url: str
    source_reliability: SourceReliability = "major_board"
    canonical_id: Optional[str] = None
    alternate_sources: List[str] = Field(default_factory=list)

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
