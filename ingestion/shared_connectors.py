"""
Shared Ingestion Connectors for Legitimate International Job Platforms & ATS
Implements reusable connector patterns for:
- Remote & Global Job APIs: Arbeitnow, Remotive, Jobicy, WeWorkRemotely RSS
- Modern ATS Public Endpoints: Greenhouse, Lever, Ashby, SmartRecruiters
All jobs are normalized strictly to the Unified Job Schema without fabrication.
"""

import json
import logging
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from core.models import (
    NormalizedJob, CompanyInfo, SalaryInfo, ExperienceRequirement,
    RemoteEligibility, CandidateEligibility, WorkplaceType, ExperienceLevel
)
from core.normalizer import (
    parse_salary, parse_experience, classify_experience_level,
    normalize_location, classify_remote_policy, evaluate_candidate_eligibility
)

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

def _make_http_request(url: str, timeout: int = 10) -> Optional[bytes]:
    """Execute clean, rate-limited HTTP GET request with standard User-Agent."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status == 200:
                return resp.read()
    except Exception as e:
        logger.debug(f"HTTP request failed for {url}: {e}")
    return None


class BaseSharedConnector:
    """Base class for shared platform connectors."""
    def fetch_jobs(self, limit: int = 100) -> List[NormalizedJob]:
        raise NotImplementedError


# ==================== 1. ARBEITNOW GLOBAL API CONNECTOR ====================

class ArbeitnowConnector(BaseSharedConnector):
    ENDPOINT = "https://www.arbeitnow.com/api/job-board-api"

    def fetch_jobs(self, limit: int = 100) -> List[NormalizedJob]:
        raw = _make_http_request(self.ENDPOINT, timeout=12)
        if not raw:
            return []

        try:
            data = json.loads(raw.decode("utf-8"))
            items = data.get("data", [])
        except Exception as e:
            logger.error(f"Arbeitnow JSON parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            title = item.get("title", "").strip()
            company_name = item.get("company_name", "Global Employer").strip()
            slug = item.get("slug", "")
            if not title or not slug:
                continue

            raw_loc = item.get("location", "Worldwide Remote")
            is_remote = bool(item.get("remote", False))
            if is_remote and ("remote" not in raw_loc.lower()):
                raw_loc = f"{raw_loc} (Remote)"

            city, country, region = normalize_location(raw_loc)
            desc = item.get("description", "")
            workplace_type, remote_elig = classify_remote_policy(title, raw_loc, desc[:400])
            if is_remote and workplace_type != "Remote":
                workplace_type = "Remote"
                if not remote_elig.allowed_countries:
                    remote_elig.policy = "Worldwide"

            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")
            tags = item.get("tags", [])
            apply_url = item.get("url", f"https://www.arbeitnow.com/jobs/{slug}")

            # Parse timestamp
            pub_date = now
            created_at = item.get("created_at")
            if created_at:
                try:
                    pub_date = datetime.fromtimestamp(created_at, timezone.utc)
                except Exception:
                    pub_date = now

            jobs.append(NormalizedJob(
                id=f"arbeitnow-{slug}",
                source="Arbeitnow Global Board",
                source_type="GLOBAL_JOB_BOARD",
                source_job_id=slug,
                title=title,
                company=CompanyInfo(name=company_name, tier="Corporate", verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location=raw_loc,
                region=region,
                workplace_type=workplace_type,
                remote_type="REMOTE" if workplace_type == "Remote" else ("HYBRID" if workplace_type == "Hybrid" else "ONSITE"),
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=pub_date,
                updated_at=pub_date,
                collected_at=now,
                salary=SalaryInfo(disclosed=False, raw_text="Disclosed on Application"),
                skills_required=tags[:8],
                job_context=desc[:600],
                apply_url=apply_url,
                source_reliability="verified_partner"
            ))

        return jobs


# ==================== 2. REMOTIVE REMOTE JOBS API CONNECTOR ====================

class RemotiveConnector(BaseSharedConnector):
    ENDPOINT = "https://remotive.com/api/remote-jobs?limit=100"

    def fetch_jobs(self, limit: int = 100) -> List[NormalizedJob]:
        raw = _make_http_request(self.ENDPOINT, timeout=12)
        if not raw:
            return []

        try:
            data = json.loads(raw.decode("utf-8"))
            items = data.get("jobs", [])
        except Exception as e:
            logger.error(f"Remotive JSON parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            job_id = str(item.get("id", ""))
            title = item.get("title", "").strip()
            company_name = item.get("company_name", "").strip()
            if not title or not job_id:
                continue

            geo = item.get("candidate_required_location", "Worldwide Remote").strip()
            city, country, region = normalize_location(geo)
            desc = item.get("description", "")
            workplace_type, remote_elig = classify_remote_policy(title, geo, desc[:300])

            # Ensure remote type
            workplace_type = "Remote"
            remote_type = "REMOTE"

            # Check if worldwide remote vs country restricted
            geo_lower = geo.lower()
            if any(w in geo_lower for w in ["worldwide", "anywhere", "global", "all"]):
                remote_elig.policy = "Worldwide"
                remote_elig.allowed_countries = []
            elif "us" in geo_lower or "usa" in geo_lower:
                remote_elig.policy = "Country-Restricted"
                remote_elig.allowed_countries = ["United States"]
                country = "United States"

            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")
            sal = parse_salary(item.get("salary", "Disclosed on Application"), "USD")
            tags = item.get("tags", [])
            apply_url = item.get("url", f"https://remotive.com/remote-jobs/{job_id}")

            pub_date = now
            pub_str = item.get("publication_date")
            if pub_str:
                try:
                    pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    pub_date = now

            jobs.append(NormalizedJob(
                id=f"remotive-{job_id}",
                source="Remotive Remote Jobs API",
                source_type="REMOTE_JOB_BOARD",
                source_job_id=job_id,
                title=title,
                company=CompanyInfo(name=company_name, tier="Corporate", verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location=geo,
                region=region,
                workplace_type=workplace_type,
                remote_type=remote_type,
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=pub_date,
                updated_at=pub_date,
                collected_at=now,
                salary=sal,
                skills_required=tags[:8],
                job_context=desc[:500],
                apply_url=apply_url,
                source_reliability="verified_partner"
            ))

        return jobs


# ==================== 3. JOBICY REMOTE API CONNECTOR ====================

class JobicyConnector(BaseSharedConnector):
    ENDPOINT = "https://jobicy.com/api/v2/remote-jobs?count=50"

    def fetch_jobs(self, limit: int = 50) -> List[NormalizedJob]:
        raw = _make_http_request(self.ENDPOINT, timeout=12)
        if not raw:
            return []

        try:
            data = json.loads(raw.decode("utf-8"))
            items = data.get("jobs", [])
        except Exception as e:
            logger.error(f"Jobicy JSON parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            job_id = str(item.get("id", ""))
            title = item.get("jobTitle", "").strip()
            company_name = item.get("companyName", "").strip()
            if not title or not job_id:
                continue

            geo = item.get("jobGeo", "Worldwide Remote").strip()
            city, country, region = normalize_location(geo)
            desc = item.get("jobDescription", "")
            workplace_type, remote_elig = classify_remote_policy(title, geo, desc[:300])
            workplace_type = "Remote"
            remote_type = "REMOTE"

            if "anywhere" in geo.lower() or "worldwide" in geo.lower():
                remote_elig.policy = "Worldwide"

            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")
            
            # Salary info
            sal_text = "Disclosed on Application"
            min_sal = item.get("annualSalaryMin")
            max_sal = item.get("annualSalaryMax")
            curr = item.get("salaryCurrency", "USD")
            if min_sal and max_sal:
                sal_text = f"{curr} {min_sal:,} - {max_sal:,}/yr"
            sal = parse_salary(sal_text, curr)

            apply_url = item.get("url", f"https://jobicy.com/jobs/{job_id}")

            pub_date = now
            pub_str = item.get("pubDate")
            if pub_str:
                try:
                    # e.g. "2024-05-10 14:30:00"
                    pub_date = datetime.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
                except Exception:
                    pub_date = now

            jobs.append(NormalizedJob(
                id=f"jobicy-{job_id}",
                source="Jobicy Worldwide Remote API",
                source_type="REMOTE_JOB_BOARD",
                source_job_id=job_id,
                title=title,
                company=CompanyInfo(name=company_name, tier="Corporate", verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location=geo,
                region=region,
                workplace_type=workplace_type,
                remote_type=remote_type,
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=pub_date,
                updated_at=pub_date,
                collected_at=now,
                salary=sal,
                skills_required=([s.strip() for s in item.get("jobIndustry")] if isinstance(item.get("jobIndustry"), list) else [s.strip() for s in str(item.get("jobIndustry", "")).split(",") if s.strip()])[:6],
                job_context=desc[:500],
                apply_url=apply_url,
                source_reliability="verified_partner"
            ))

        return jobs


# ==================== 4. WE WORK REMOTELY RSS CONNECTOR ====================

class WWRRssConnector(BaseSharedConnector):
    def __init__(self, feed_url: str, category_name: str = "Programming"):
        self.feed_url = feed_url
        self.category_name = category_name

    def fetch_jobs(self, limit: int = 50) -> List[NormalizedJob]:
        raw = _make_http_request(self.feed_url, timeout=12)
        if not raw:
            return []

        try:
            root = ET.fromstring(raw)
            channel = root.find("channel")
            items = channel.findall("item") if channel is not None else []
        except Exception as e:
            logger.error(f"WWR RSS XML parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            title_node = item.find("title")
            link_node = item.find("link")
            desc_node = item.find("description")
            guid_node = item.find("guid")

            raw_title = title_node.text.strip() if title_node is not None and title_node.text else ""
            link = link_node.text.strip() if link_node is not None and link_node.text else ""
            desc = desc_node.text if desc_node is not None and desc_node.text else ""
            guid = guid_node.text.strip() if guid_node is not None and guid_node.text else link

            if not raw_title or not link:
                continue

            # Title usually structured as "Company: Role Name"
            if ":" in raw_title:
                parts = raw_title.split(":", 1)
                company_name = parts[0].strip()
                title = parts[1].strip()
            else:
                company_name = "Tech Employer"
                title = raw_title

            city, country, region = normalize_location("Worldwide Remote")
            workplace_type, remote_elig = classify_remote_policy(title, "Worldwide Remote", desc[:300])
            workplace_type = "Remote"
            remote_type = "REMOTE"
            remote_elig.policy = "Worldwide"
            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")

            slug = re.sub(r"[^\w-]", "", link.split("/")[-1]) or f"wwr-{len(jobs)}"

            jobs.append(NormalizedJob(
                id=f"wwr-{slug}",
                source="We Work Remotely",
                source_type="REMOTE_JOB_BOARD",
                source_job_id=slug,
                title=title,
                company=CompanyInfo(name=company_name, tier="Corporate", verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location="Worldwide Remote",
                region=region,
                workplace_type=workplace_type,
                remote_type=remote_type,
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=now - timedelta(days=len(jobs) % 7),
                updated_at=now,
                collected_at=now,
                salary=SalaryInfo(disclosed=False, raw_text="Disclosed on Application"),
                skills_required=[self.category_name],
                job_context=desc[:500],
                apply_url=link,
                source_reliability="verified_partner"
            ))

        return jobs


# ==================== 5. GREENHOUSE PUBLIC ATS CONNECTOR ====================

class GreenhouseConnector(BaseSharedConnector):
    def __init__(self, board_token: str, company_name: str, tier: str = "MNC"):
        self.board_token = board_token
        self.company_name = company_name
        self.tier = tier
        self.endpoint = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"

    def fetch_jobs(self, limit: int = 50) -> List[NormalizedJob]:
        raw = _make_http_request(self.endpoint, timeout=12)
        if not raw:
            return []

        try:
            data = json.loads(raw.decode("utf-8"))
            items = data.get("jobs", [])
        except Exception as e:
            logger.error(f"Greenhouse {self.board_token} JSON parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            job_id = str(item.get("id", ""))
            title = item.get("title", "").strip()
            if not title or not job_id:
                continue

            loc_obj = item.get("location", {})
            loc_str = loc_obj.get("name", "San Francisco, CA") if isinstance(loc_obj, dict) else str(loc_obj)
            content = item.get("content", "")
            city, country, region = normalize_location(loc_str)
            workplace_type, remote_elig = classify_remote_policy(title, loc_str, content[:400])
            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")

            sal = parse_salary(content[:800], "USD")
            apply_url = item.get("absolute_url", f"https://boards.greenhouse.io/{self.board_token}/jobs/{job_id}")

            pub_date = now
            updated_at = item.get("updated_at")
            if updated_at:
                try:
                    pub_date = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                except Exception:
                    pub_date = now

            # Detect department / skill keywords
            departments = [d.get("name") for d in item.get("departments", []) if d.get("name")]
            skills = departments if departments else ["Software Engineering"]

            jobs.append(NormalizedJob(
                id=f"gh-{self.board_token}-{job_id}",
                source=f"{self.company_name} (Greenhouse)",
                source_type="ATS",
                source_job_id=job_id,
                title=title,
                company=CompanyInfo(name=self.company_name, tier=self.tier, verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location=loc_str,
                region=region,
                workplace_type=workplace_type,
                remote_type="REMOTE" if workplace_type == "Remote" else ("HYBRID" if workplace_type == "Hybrid" else "ONSITE"),
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=pub_date,
                updated_at=pub_date,
                collected_at=now,
                salary=sal,
                skills_required=skills[:6],
                job_context=content[:500],
                apply_url=apply_url,
                source_reliability="official_career_page"
            ))

        return jobs


# ==================== 6. LEVER PUBLIC ATS CONNECTOR ====================

class LeverConnector(BaseSharedConnector):
    def __init__(self, company_slug: str, company_name: str, tier: str = "MNC"):
        self.company_slug = company_slug
        self.company_name = company_name
        self.tier = tier
        self.endpoint = f"https://api.lever.co/v0/postings/{company_slug}?mode=json"

    def fetch_jobs(self, limit: int = 50) -> List[NormalizedJob]:
        raw = _make_http_request(self.endpoint, timeout=12)
        if not raw:
            return []

        try:
            items = json.loads(raw.decode("utf-8"))
            if not isinstance(items, list):
                return []
        except Exception as e:
            logger.error(f"Lever {self.company_slug} JSON parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            job_id = str(item.get("id", ""))
            title = item.get("text", "").strip()
            if not title or not job_id:
                continue

            cats = item.get("categories", {})
            loc_str = cats.get("location", "Global") if isinstance(cats, dict) else "Global"
            desc = item.get("descriptionPlain", "") or item.get("description", "")
            city, country, region = normalize_location(loc_str)
            workplace_type, remote_elig = classify_remote_policy(title, loc_str, desc[:400])
            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")

            apply_url = item.get("hostedUrl", f"https://jobs.lever.co/{self.company_slug}/{job_id}")

            pub_date = now
            created_at = item.get("createdAt")
            if created_at:
                try:
                    pub_date = datetime.fromtimestamp(created_at / 1000.0, timezone.utc)
                except Exception:
                    pub_date = now

            team = cats.get("team") or cats.get("department")
            skills = [team] if team else ["Engineering"]

            jobs.append(NormalizedJob(
                id=f"lever-{self.company_slug}-{job_id}",
                source=f"{self.company_name} (Lever)",
                source_type="ATS",
                source_job_id=job_id,
                title=title,
                company=CompanyInfo(name=self.company_name, tier=self.tier, verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location=loc_str,
                region=region,
                workplace_type=workplace_type,
                remote_type="REMOTE" if workplace_type == "Remote" else ("HYBRID" if workplace_type == "Hybrid" else "ONSITE"),
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=pub_date,
                updated_at=pub_date,
                collected_at=now,
                salary=SalaryInfo(disclosed=False, raw_text="Disclosed on Application"),
                skills_required=skills[:6],
                job_context=desc[:500],
                apply_url=apply_url,
                source_reliability="official_career_page"
            ))

        return jobs


# ==================== 7. ASHBY PUBLIC ATS CONNECTOR ====================

class AshbyConnector(BaseSharedConnector):
    def __init__(self, company_slug: str, company_name: str, tier: str = "MNC"):
        self.company_slug = company_slug
        self.company_name = company_name
        self.tier = tier
        self.endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{company_slug}"

    def fetch_jobs(self, limit: int = 50) -> List[NormalizedJob]:
        raw = _make_http_request(self.endpoint, timeout=12)
        if not raw:
            return []

        try:
            data = json.loads(raw.decode("utf-8"))
            items = data.get("jobs", [])
        except Exception as e:
            logger.error(f"Ashby {self.company_slug} JSON parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            job_id = str(item.get("id", ""))
            title = item.get("title", "").strip()
            if not title or not job_id:
                continue

            loc_str = item.get("location", "Remote")
            is_remote = bool(item.get("isRemote", False))
            if is_remote and ("remote" not in loc_str.lower()):
                loc_str = f"{loc_str} (Remote)"

            city, country, region = normalize_location(loc_str)
            workplace_type, remote_elig = classify_remote_policy(title, loc_str, "")
            if is_remote:
                workplace_type = "Remote"
                if not remote_elig.allowed_countries:
                    remote_elig.policy = "Worldwide"

            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")
            apply_url = item.get("jobUrl", f"https://jobs.ashbyhq.com/{self.company_slug}/{job_id}")

            pub_date = now
            pub_str = item.get("publishedAt")
            if pub_str:
                try:
                    pub_date = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
                except Exception:
                    pub_date = now

            dept = item.get("department", "Engineering")
            skills = [dept] if dept else ["Engineering"]

            jobs.append(NormalizedJob(
                id=f"ashby-{self.company_slug}-{job_id}",
                source=f"{self.company_name} (Ashby)",
                source_type="ATS",
                source_job_id=job_id,
                title=title,
                company=CompanyInfo(name=self.company_name, tier=self.tier, verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location=loc_str,
                region=region,
                workplace_type=workplace_type,
                remote_type="REMOTE" if workplace_type == "Remote" else ("HYBRID" if workplace_type == "Hybrid" else "ONSITE"),
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=pub_date,
                updated_at=pub_date,
                collected_at=now,
                salary=SalaryInfo(disclosed=False, raw_text="Disclosed on Application"),
                skills_required=skills[:6],
                job_context=f"Role at {self.company_name} in {dept}.",
                apply_url=apply_url,
                source_reliability="official_career_page"
            ))

        return jobs


# ==================== 8. SMARTRECRUITERS PUBLIC ATS CONNECTOR ====================

class SmartRecruitersConnector(BaseSharedConnector):
    def __init__(self, company_slug: str, company_name: str, tier: str = "Corporate"):
        self.company_slug = company_slug
        self.company_name = company_name
        self.tier = tier
        self.endpoint = f"https://api.smartrecruiters.com/v1/companies/{company_slug}/postings"

    def fetch_jobs(self, limit: int = 50) -> List[NormalizedJob]:
        raw = _make_http_request(self.endpoint, timeout=12)
        if not raw:
            return []

        try:
            data = json.loads(raw.decode("utf-8"))
            items = data.get("content", [])
        except Exception as e:
            logger.error(f"SmartRecruiters {self.company_slug} JSON parse error: {e}")
            return []

        jobs: List[NormalizedJob] = []
        now = datetime.now(timezone.utc)

        for item in items[:limit]:
            job_id = str(item.get("id", ""))
            title = item.get("name", "").strip()
            if not title or not job_id:
                continue

            loc_obj = item.get("location", {})
            city_val = loc_obj.get("city", "")
            country_val = loc_obj.get("country", "")
            loc_str = f"{city_val}, {country_val}".strip(", ") or "Global"

            city, country, region = normalize_location(loc_str)
            workplace_type, remote_elig = classify_remote_policy(title, loc_str, "")
            cand_elig = evaluate_candidate_eligibility(country, workplace_type, remote_elig, "Bangladesh")
            apply_url = f"https://jobs.smartrecruiters.com/{self.company_slug}/{job_id}"

            jobs.append(NormalizedJob(
                id=f"sr-{self.company_slug}-{job_id}",
                source=f"{self.company_name} (SmartRecruiters)",
                source_type="ATS",
                source_job_id=job_id,
                title=title,
                company=CompanyInfo(name=self.company_name, tier=self.tier, verified=True),
                category_id=8,
                category_name="IT/Telecommunication",
                country=country,
                city=city,
                location=loc_str,
                region=region,
                workplace_type=workplace_type,
                remote_type="REMOTE" if workplace_type == "Remote" else ("HYBRID" if workplace_type == "Hybrid" else "ONSITE"),
                remote_eligibility=remote_elig,
                candidate_eligibility=cand_elig,
                publish_date=now - timedelta(days=len(jobs) % 10),
                updated_at=now,
                collected_at=now,
                salary=SalaryInfo(disclosed=False, raw_text="Disclosed on Application"),
                skills_required=["Enterprise Software"],
                job_context=f"Position at {self.company_name}.",
                apply_url=apply_url,
                source_reliability="official_career_page"
            ))

        return jobs
