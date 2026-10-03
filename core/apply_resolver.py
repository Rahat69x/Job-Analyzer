"""
Universal Job Application Resolver & Anti-Redirect ATS Engine
Provides reliable international job application recognition, canonical ATS unrolling,
authentication barrier detection, and step-by-step workflow guidance.
Strictly excludes Bangladesh-specific platforms (BDJobs) from international flows.
"""

import re
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field

# ==================== CONSTANTS & SIGNATURES ====================

BANGLADESH_DOMAINS = [
    "bdjobs.com",
    "jobs.bdjobs.com",
    "api.bdjobs.com",
    "corporate3.bdjobs.com",
    "mybdjobs.bdjobs.com",
    "chakri.com",
    "skill.jobs"
]

# Comprehensive Known ATS Signatures (Extensible, regex-backed)
ATS_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "Workday": {
        "patterns": [
            r"myworkdayjobs\.com",
            r"wd\d+\.myworkday\.com",
            r"workday\.com/.+/job",
            r"myworkday\.com"
        ],
        "auth_required": True,
        "auth_details": "Workday requires candidate account sign-in or registration for each employer.",
        "steps": [
            "Sign in with your Workday applicant account or click 'Create Account'.",
            "Upload your resume/CV for automatic field parsing.",
            "Review parsed experience and education details.",
            "Paste your tailored pitch/cover letter in the supplementary section.",
            "Review disclosures and submit your application."
        ]
    },
    "Greenhouse": {
        "patterns": [
            r"boards\.greenhouse\.io",
            r"job-boards\.greenhouse\.io",
            r"greenhouse\.io",
            r"[?&]gh_jid=\d+"
        ],
        "auth_required": False,
        "auth_details": "Direct single-page ATS form. No login account required.",
        "steps": [
            "Fill out personal contact details (Name, Email, Phone, Location).",
            "Upload your resume/CV (PDF format recommended).",
            "Paste your tailored pitch into the Cover Letter field.",
            "Complete role-specific screening questions and submit."
        ]
    },
    "Lever": {
        "patterns": [
            r"jobs\.lever\.co",
            r"lever\.co"
        ],
        "auth_required": False,
        "auth_details": "Direct lightweight application form. No login required.",
        "steps": [
            "Provide basic information and attach your resume/CV.",
            "Fill in links to LinkedIn, GitHub, or portfolio if applicable.",
            "Paste your tailored pitch into the additional info section.",
            "Submit application directly to the recruiting team."
        ]
    },
    "SmartRecruiters": {
        "patterns": [
            r"jobs\.smartrecruiters\.com",
            r"smartrecruiters\.com"
        ],
        "auth_required": False,
        "auth_details": "Single-page ATS form with optional SmartRecruiters profile sign-in.",
        "steps": [
            "Choose 'Apply without account' or sign in with SmartRecruiters/LinkedIn.",
            "Upload resume and confirm personal contact information.",
            "Answer job-specific screening questions.",
            "Review and submit."
        ]
    },
    "Ashby": {
        "patterns": [
            r"jobs\.ashbyhq\.com",
            r"ashbyhq\.com"
        ],
        "auth_required": False,
        "auth_details": "Fast modern ATS application form. No login required.",
        "steps": [
            "Fill out candidate contact information.",
            "Attach resume/CV and portfolio/GitHub links.",
            "Paste your tailored pitch note.",
            "Submit application directly."
        ]
    },
    "BambooHR": {
        "patterns": [
            r"[\w-]+\.bamboohr\.com/(?:careers|jobs)",
            r"bamboohr\.com"
        ],
        "auth_required": False,
        "auth_details": "Standard direct application form.",
        "steps": [
            "Enter candidate contact information.",
            "Upload resume and complete employment history.",
            "Submit application."
        ]
    },
    "Taleo / Oracle Cloud": {
        "patterns": [
            r"[\w-]+\.taleo\.net",
            r"oraclecloud\.com/.+/career",
            r"taleo\.net"
        ],
        "auth_required": True,
        "auth_details": "Enterprise Oracle/Taleo applicant portal requiring account login.",
        "steps": [
            "Register or sign in with your enterprise applicant account.",
            "Upload resume and step through multi-page application wizard.",
            "Complete compliance and background questionnaire.",
            "Submit application."
        ]
    },
    "iCIMS": {
        "patterns": [
            r"[\w-]+\.icims\.com/jobs",
            r"icims\.com"
        ],
        "auth_required": True,
        "auth_details": "iCIMS talent portal; registration or social sign-in typically required.",
        "steps": [
            "Sign in or register with email / social login.",
            "Upload CV and review parsed profile data.",
            "Answer employer screening questions and submit."
        ]
    },
    "SuccessFactors / SAP": {
        "patterns": [
            r"career\d*\.successfactors\.com",
            r"jobs\.sap\.com"
        ],
        "auth_required": True,
        "auth_details": "SAP SuccessFactors enterprise applicant registration required.",
        "steps": [
            "Create or sign in to your enterprise candidate profile.",
            "Complete profile information and upload documents.",
            "Submit your application."
        ]
    },
    "Workable": {
        "patterns": [
            r"apply\.workable\.com",
            r"[\w-]+\.workable\.com"
        ],
        "auth_required": False,
        "auth_details": "Direct multi-field form or 1-click LinkedIn autofill.",
        "steps": [
            "Fill in personal details or autofill via LinkedIn.",
            "Upload resume and cover note.",
            "Submit application."
        ]
    },
    "Breezy HR": {
        "patterns": [
            r"[\w-]+\.breezy\.hr"
        ],
        "auth_required": False,
        "auth_details": "Direct modern form without login wall.",
        "steps": [
            "Enter candidate details and attach resume.",
            "Submit application directly."
        ]
    },
    "Jobvite": {
        "patterns": [
            r"jobs\.jobvite\.com"
        ],
        "auth_required": False,
        "auth_details": "Jobvite ATS application portal.",
        "steps": [
            "Fill in contact info and upload resume.",
            "Review answers and submit."
        ]
    }
}

# Major Global Job Boards
JOB_BOARD_SIGNATURES: Dict[str, Dict[str, Any]] = {
    "LinkedIn": {
        "patterns": [
            r"linkedin\.com/jobs",
            r"linkedin\.com/comm/jobs"
        ],
        "auth_required": True,
        "auth_details": "Requires LinkedIn account sign-in. May offer 1-click 'Easy Apply' or external employer redirect.",
        "steps": [
            "Ensure you are signed in to your LinkedIn account.",
            "If 'Easy Apply' is present, review pre-filled profile details and submit.",
            "If 'Apply on company website' is shown, proceed to external employer portal."
        ]
    },
    "Indeed": {
        "patterns": [
            r"indeed\.com/viewjob",
            r"indeed\.com/rc/clk",
            r"indeed\.com/jobs",
            r"[\w-]+\.indeed\.com"
        ],
        "auth_required": False,
        "auth_details": "Offers direct 'Indeed Apply' (optional login) or external employer redirects.",
        "steps": [
            "Review job posting details.",
            "Click 'Apply Now' to submit via Indeed or follow external redirect to company ATS."
        ]
    },
    "Glassdoor": {
        "patterns": [
            r"glassdoor\.com/job-listing",
            r"glassdoor\.com/partner/jobListing\.htm",
            r"glassdoor\.com/Jobs"
        ],
        "auth_required": False,
        "auth_details": "Aggregator routing to company career site or direct apply partner.",
        "steps": [
            "Click 'Apply on Company Site' to unwrap direct employer application."
        ]
    },
    "Wellfound": {
        "patterns": [
            r"wellfound\.com/jobs",
            r"angel\.co/company/.+/jobs"
        ],
        "auth_required": True,
        "auth_details": "Requires Wellfound (AngelList) candidate profile to message founders/recruiters.",
        "steps": [
            "Sign in with your Wellfound profile.",
            "Write a personalized pitch note to the hiring manager.",
            "Submit application directly through Wellfound platform."
        ]
    },
    "ZipRecruiter": {
        "patterns": [
            r"ziprecruiter\.com/jobs",
            r"ziprecruiter\.com/c/.+/job"
        ],
        "auth_required": False,
        "auth_details": "1-click apply with email or external ATS redirect.",
        "steps": [
            "Enter your email address to submit application directly or proceed to employer site."
        ]
    },
    "Monster": {
        "patterns": [
            r"monster\.com/job-openings",
            r"monster\.com/jobs",
            r"job-openings\.monster\.com"
        ],
        "auth_required": False,
        "auth_details": "Aggregator link unrolling to company ATS or partner portal.",
        "steps": [
            "Follow unrolled employer link to complete application."
        ]
    },
    "Remote OK": {
        "patterns": [
            r"remoteok\.com/remote-jobs",
            r"remoteok\.io"
        ],
        "auth_required": False,
        "auth_details": "Direct remote listing linking out to company ATS or apply email.",
        "steps": [
            "Follow direct link to the employer's canonical remote application endpoint."
        ]
    },
    "We Work Remotely": {
        "patterns": [
            r"weworkremotely\.com/remote-jobs"
        ],
        "auth_required": False,
        "auth_details": "Curated remote job platform with direct links to employer ATS.",
        "steps": [
            "Click 'Apply for this position' to open the employer's ATS application form."
        ]
    }
}


# ==================== RESPONSE SCHEMA ====================

class ApplicationResolution(BaseModel):
    status: str = "resolved" # "resolved", "manual_action_required", "redirect_unwrapped"
    application_type: str # "EXTERNAL_ATS", "DIRECT_JOB_BOARD", "COMPANY_CAREER_SITE", "QUICK_APPLY"
    platform_name: str
    canonical_url: str
    original_url: str
    is_direct: bool
    auth_requirement: str # "NONE", "AUTH_REQUIRED", "CAPTCHA_CHECK", "MANUAL_STEP_REQUIRED"
    auth_details: str
    steps: List[str]
    is_bangladesh_excluded: bool = True
    notice: Optional[str] = None
    preserved_payload: Dict[str, Any] = Field(default_factory=dict)


# ==================== ENGINE IMPLEMENTATION ====================

class JobApplicationResolver:
    """
    Intelligent Link Verification, ATS Resolver, and Application Flow Engine.
    Handles international platforms, unwraps redirects, detects barriers,
    and strictly forbids routing international jobs to BDJobs.
    """

    def is_bangladesh_url(self, url: str) -> bool:
        """Checks if URL belongs to any Bangladesh-specific platform."""
        if not url:
            return False
        try:
            parsed = urllib.parse.urlparse(url)
            host = (parsed.hostname or "").lower()
            return any(bd in host for bd in BANGLADESH_DOMAINS)
        except Exception:
            return False

    def unwrap_redirect(self, url: str) -> str:
        """
        Unwraps aggregator nested redirect URLs (e.g. Monster, Indeed, affiliate tracking).
        Strips unnecessary telemetry while preserving canonical job IDs.
        """
        if not url:
            return ""
        
        current_url = url.strip()
        nested_param_keys = ["redirectUrl", "redirect_url", "url", "dest", "target", "r", "out", "link", "jobUrl", "to"]
        
        # Unwrap up to 4 levels of nested redirects
        for _ in range(4):
            try:
                parsed = urllib.parse.urlparse(current_url)
                params = urllib.parse.parse_qs(parsed.query)
                found_nested = False
                for key in nested_param_keys:
                    if key in params and params[key]:
                        candidate = params[key][0]
                        if candidate.startswith("http://") or candidate.startswith("https://"):
                            current_url = urllib.parse.unquote(candidate)
                            found_nested = True
                            break
                if not found_nested:
                    break
            except Exception:
                break
        
        # Clean telemetry parameters but preserve core ATS params
        try:
            parsed = urllib.parse.urlparse(current_url)
            query_params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
            tracking_keys = {
                "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
                "fbclid", "gclid", "ref", "trk", "trkinfo", "refid", "trackingid", "source"
            }
            cleaned_params = {k: v for k, v in query_params.items() if k.lower() not in tracking_keys}
            
            # Reconstruct query string
            new_query = urllib.parse.urlencode(cleaned_params, doseq=True)
            cleaned_url = urllib.parse.urlunparse((
                parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment
            ))
            return cleaned_url if cleaned_url.startswith("http") else current_url
        except Exception:
            return current_url

    def resolve_application(
        self,
        job_id: str,
        apply_url: str,
        job_title: str = "",
        company_name: str = "",
        location: str = "",
        skills: Optional[List[str]] = None,
        job_source: str = "Global"
    ) -> ApplicationResolution:
        """
        Resolves the true application target, recognizes flow type,
        checks for auth barriers, and prevents Bangladesh platform pollution.
        """
        skills = skills or []
        original_url = apply_url or ""
        unwrapped_url = self.unwrap_redirect(original_url)

        # Strict Bangladesh / BDJobs Exclusion Check
        is_bd_platform = self.is_bangladesh_url(unwrapped_url) or self.is_bangladesh_url(original_url) or job_source.lower() == "bdjobs"
        notice_message = None

        if is_bd_platform:
            # If an international or global job was erroneously linked to BDJobs, override with canonical global search fallback
            clean_company = re.sub(r"[^\w\s-]", "", company_name).strip()
            clean_title = re.sub(r"[^\w\s-]", "", job_title).strip()
            
            # Fallback to direct company career destination
            canonical_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(clean_company)}+{urllib.parse.quote_plus(clean_title)}+careers"
            notice_message = "Bangladesh-specific platforms (BDJobs) are excluded for international applications. Re-routed to employer canonical careers endpoint."
            
            return ApplicationResolution(
                status="redirect_unwrapped",
                application_type="COMPANY_CAREER_SITE",
                platform_name=f"{company_name} Career Portal",
                canonical_url=canonical_url,
                original_url=original_url,
                is_direct=True,
                auth_requirement="NONE",
                auth_details="Direct employer careers portal search.",
                steps=[
                    f"Open official career requisition for {clean_company}.",
                    "Follow direct application instructions on employer portal.",
                    "Paste your preserved pitch note and upload your CV."
                ],
                is_bangladesh_excluded=True,
                notice=notice_message,
                preserved_payload=self._build_preserved_payload(job_id, job_title, company_name, location, skills, canonical_url)
            )

        # 1. Check Known ATS Systems
        for ats_name, config in ATS_SIGNATURES.items():
            for pattern in config["patterns"]:
                if re.search(pattern, unwrapped_url, re.IGNORECASE):
                    return ApplicationResolution(
                        status="resolved",
                        application_type="EXTERNAL_ATS",
                        platform_name=ats_name,
                        canonical_url=unwrapped_url,
                        original_url=original_url,
                        is_direct=True,
                        auth_requirement="AUTH_REQUIRED" if config["auth_required"] else "NONE",
                        auth_details=config["auth_details"],
                        steps=config["steps"],
                        is_bangladesh_excluded=True,
                        preserved_payload=self._build_preserved_payload(job_id, job_title, company_name, location, skills, unwrapped_url)
                    )

        # 2. Check Known Job Boards
        for board_name, config in JOB_BOARD_SIGNATURES.items():
            for pattern in config["patterns"]:
                if re.search(pattern, unwrapped_url, re.IGNORECASE):
                    return ApplicationResolution(
                        status="resolved",
                        application_type="DIRECT_JOB_BOARD",
                        platform_name=board_name,
                        canonical_url=unwrapped_url,
                        original_url=original_url,
                        is_direct=True,
                        auth_requirement="AUTH_REQUIRED" if config["auth_required"] else "NONE",
                        auth_details=config["auth_details"],
                        steps=config["steps"],
                        is_bangladesh_excluded=True,
                        preserved_payload=self._build_preserved_payload(job_id, job_title, company_name, location, skills, unwrapped_url)
                    )

        # 3. Check for Quick / Email Apply
        if unwrapped_url.startswith("mailto:"):
            email_addr = unwrapped_url.replace("mailto:", "").split("?")[0]
            return ApplicationResolution(
                status="resolved",
                application_type="QUICK_APPLY",
                platform_name="Direct Email Apply",
                canonical_url=unwrapped_url,
                original_url=original_url,
                is_direct=True,
                auth_requirement="NONE",
                auth_details=f"Direct email submission to {email_addr}. No login wall.",
                steps=[
                    f"Send your application email to: {email_addr}",
                    f"Subject: Application for {job_title} - [Your Name]",
                    "Attach your tailored CV/Resume (PDF).",
                    "Paste your pre-formatted application pitch note into the email body."
                ],
                is_bangladesh_excluded=True,
                preserved_payload=self._build_preserved_payload(job_id, job_title, company_name, location, skills, unwrapped_url)
            )

        # 4. Check for Generic ATS / Career Subdomains (Heuristic Pattern Matcher)
        # Supports ANY international ATS or career platform not in the explicit list
        parsed = urllib.parse.urlparse(unwrapped_url)
        host = (parsed.hostname or "").lower()
        path = (parsed.path or "").lower()

        is_ats_subdomain = any(term in host for term in ["jobs.", "careers.", "career.", "recruiting.", "talent.", "apply.", "join."])
        is_ats_path = any(term in path for term in ["/jobs/", "/careers/", "/career/", "/openings/", "/apply/", "/requisition/"])
        has_ats_tokens = any(k in parsed.query.lower() for k in ["jid=", "reqid=", "req_id=", "jobid=", "job_id="])

        if is_ats_subdomain or is_ats_path or has_ats_tokens:
            detected_name = host.split(".")[0].capitalize() if is_ats_subdomain else f"{company_name or 'Company'} Portal"
            return ApplicationResolution(
                status="resolved",
                application_type="EXTERNAL_ATS",
                platform_name=f"{detected_name} (Applicant Tracking System)",
                canonical_url=unwrapped_url,
                original_url=original_url,
                is_direct=True,
                auth_requirement="MANUAL_STEP_REQUIRED",
                auth_details="External ATS application form. Candidate verification or resume upload required.",
                steps=[
                    f"Proceed to {detected_name} official application page.",
                    "Fill in your candidate contact information.",
                    "Upload your CV/Resume.",
                    "Paste your tailored pitch note in the Cover Letter field.",
                    "Submit application."
                ],
                is_bangladesh_excluded=True,
                preserved_payload=self._build_preserved_payload(job_id, job_title, company_name, location, skills, unwrapped_url)
            )

        # 5. Default Company Career-Site Application
        platform_label = f"{company_name} Official Portal" if company_name else "Direct Career Portal"
        return ApplicationResolution(
            status="resolved",
            application_type="COMPANY_CAREER_SITE",
            platform_name=platform_label,
            canonical_url=unwrapped_url,
            original_url=original_url,
            is_direct=True,
            auth_requirement="MANUAL_STEP_REQUIRED",
            auth_details="Direct career portal application.",
            steps=[
                f"Open the official job posting on {platform_label}.",
                "Review requirements and click the employer's Apply button.",
                "Complete the application questionnaire with your preserved profile data."
            ],
            is_bangladesh_excluded=True,
            preserved_payload=self._build_preserved_payload(job_id, job_title, company_name, location, skills, unwrapped_url)
        )

    def _build_preserved_payload(
        self,
        job_id: str,
        title: str,
        company: str,
        location: str,
        skills: List[str],
        canonical_url: str
    ) -> Dict[str, Any]:
        """Creates a ready-to-use candidate clipboard payload preserving job and application data."""
        skills_str = ", ".join(skills[:6]) if skills else "Data & Software Engineering"
        tailored_pitch = (
            f"Dear Hiring Team at {company or 'the hiring organization'},\n\n"
            f"I am writing to express my strong interest in the {title or 'open position'} opportunity. "
            f"With proven hands-on expertise in {skills_str}, I bring strong analytical problem-solving, "
            f"collaborative execution, and a track record of delivering measurable impact. "
            f"I welcome the opportunity to discuss how my skill set aligns with your team's goals.\n\n"
            f"Thank you for your consideration,\nCandidate"
        )

        return {
            "job_id": job_id,
            "job_title": title,
            "company_name": company,
            "location": location,
            "skills": skills,
            "canonical_url": canonical_url,
            "tailored_pitch": tailored_pitch,
            "quick_summary": f"{title} at {company} ({location})"
        }


# Global Singleton Instance
apply_resolver = JobApplicationResolver()
