"""
Single Source Registry & Architecture for Global Job Discovery
Houses structured metadata for 60-70+ legitimate international and regional sources.
Enforces real live health status tracking, category grouping, and strict Bdjobs isolation.
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

# Supported Source Types (Section 1)
SOURCE_TYPES = [
    "GLOBAL_JOB_BOARD",
    "REMOTE_JOB_BOARD",
    "COMPANY_CAREER_PAGE",
    "ATS",
    "GOVERNMENT_JOB_PORTAL",
    "ENGINEERING_JOB_BOARD",
    "STARTUP_JOB_BOARD",
    "FREELANCE_CONTRACT",
    "REGIONAL_JOB_BOARD"
]

# UI Grouping Categories (Section 16)
SOURCE_CATEGORIES = [
    "Global Job Boards",
    "Remote Job Boards",
    "ATS / Career Systems",
    "Company Careers",
    "Regional Sources",
    "Government Sources",
    "Bangladesh Sources"
]

class SourceMetadata(BaseModel):
    id: str
    name: str
    type: str # One of SOURCE_TYPES
    region: str # Global, United States, Europe, India, Bangladesh, etc.
    category: str # One of SOURCE_CATEGORIES
    enabled: bool = True
    access_method: str # PUBLIC_API, RSS_FEED, ATS_CONNECTOR, STRUCTURED_FEED, DIRECT_CAREER
    endpoint: str
    parser: str # arbeitnow, remotive, jobicy, greenhouse, lever, ashby, smartrecruiters, wwr_rss, bdjobs, etc.
    company_slug: Optional[str] = None
    company_tier: Optional[str] = "Corporate"
    last_success: Optional[str] = None
    last_attempt: Optional[str] = None
    last_error: Optional[str] = None
    jobs_found: int = 0
    jobs_deduped: int = 0
    status: str = "UNAVAILABLE" # ACTIVE, PARTIAL, UNAVAILABLE, ERROR
    http_status: Optional[int] = None
    notes: Optional[str] = None

class SourceRegistry:
    """
    Central thread-safe registry tracking 70+ job sources, their health,
    endpoint specifications, and retrieval statistics.
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._sources: Dict[str, SourceMetadata] = {}
        self._registry_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "data", 
            "source_registry_state.json"
        )
        self._initialize_registry()
        self._load_state()

    def _initialize_registry(self):
        """Register the comprehensive list of 70 legitimate job sources."""
        raw_catalog = [
            # ==================== 1. GLOBAL JOB BOARDS (7) ====================
            {
                "id": "arbeitnow", "name": "Arbeitnow Global Board", "type": "GLOBAL_JOB_BOARD",
                "region": "Europe/Global", "category": "Global Job Boards", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://www.arbeitnow.com/api/job-board-api",
                "parser": "arbeitnow"
            },
            {
                "id": "indeed_global", "name": "Indeed Global Catalog", "type": "GLOBAL_JOB_BOARD",
                "region": "Global", "category": "Global Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://www.indeed.com/jobs",
                "parser": "indeed_global"
            },
            {
                "id": "linkedin_global", "name": "LinkedIn Global Jobs", "type": "GLOBAL_JOB_BOARD",
                "region": "Global", "category": "Global Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://www.linkedin.com/jobs",
                "parser": "linkedin_global"
            },
            {
                "id": "glassdoor_global", "name": "Glassdoor International", "type": "GLOBAL_JOB_BOARD",
                "region": "Global", "category": "Global Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://www.glassdoor.com/Jobs",
                "parser": "glassdoor_global"
            },
            {
                "id": "ziprecruiter_global", "name": "ZipRecruiter Public", "type": "GLOBAL_JOB_BOARD",
                "region": "United States/Global", "category": "Global Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://www.ziprecruiter.com/jobs",
                "parser": "ziprecruiter_global"
            },
            {
                "id": "monster_global", "name": "Monster Worldwide", "type": "GLOBAL_JOB_BOARD",
                "region": "Global", "category": "Global Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://www.monster.com/jobs",
                "parser": "monster_global"
            },
            {
                "id": "careerjet_global", "name": "Careerjet Global Search", "type": "GLOBAL_JOB_BOARD",
                "region": "Global", "category": "Global Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://www.careerjet.com",
                "parser": "careerjet_global"
            },

            # ==================== 2. REMOTE JOB BOARDS (11) ====================
            {
                "id": "remotive", "name": "Remotive Remote Jobs API", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://remotive.com/api/remote-jobs",
                "parser": "remotive"
            },
            {
                "id": "jobicy", "name": "Jobicy Worldwide Remote API", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://jobicy.com/api/v2/remote-jobs",
                "parser": "jobicy"
            },
            {
                "id": "wwr_prog", "name": "We Work Remotely - Programming", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "RSS_FEED", "endpoint": "https://weworkremotely.com/categories/remote-programming-jobs.rss",
                "parser": "wwr_rss"
            },
            {
                "id": "wwr_devops", "name": "We Work Remotely - DevOps & Sysadmin", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "RSS_FEED", "endpoint": "https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss",
                "parser": "wwr_rss"
            },
            {
                "id": "wwr_design", "name": "We Work Remotely - Design", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "RSS_FEED", "endpoint": "https://weworkremotely.com/categories/remote-design-jobs.rss",
                "parser": "wwr_rss"
            },
            {
                "id": "wwr_product", "name": "We Work Remotely - Product", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "RSS_FEED", "endpoint": "https://weworkremotely.com/categories/remote-product-jobs.rss",
                "parser": "wwr_rss"
            },
            {
                "id": "wwr_management", "name": "We Work Remotely - Management & Finance", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "RSS_FEED", "endpoint": "https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss",
                "parser": "wwr_rss"
            },
            {
                "id": "remoteok", "name": "Remote OK Feed", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://remoteok.com/api",
                "parser": "remoteok"
            },
            {
                "id": "himalayas", "name": "Himalayas Tech Remote", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://himalayas.app/jobs",
                "parser": "himalayas"
            },
            {
                "id": "workingnomads", "name": "Working Nomads", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://www.workingnomads.com/jobs",
                "parser": "workingnomads"
            },
            {
                "id": "justremote", "name": "JustRemote Board", "type": "REMOTE_JOB_BOARD",
                "region": "Worldwide", "category": "Remote Job Boards", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://justremote.co",
                "parser": "justremote"
            },

            # ==================== 3. ATS / CAREER SYSTEMS (35) ====================
            # Greenhouse ATS (15)
            {
                "id": "gh_anthropic", "name": "Anthropic Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs", "parser": "greenhouse",
                "company_slug": "anthropic", "company_tier": "MNC"
            },
            {
                "id": "gh_stripe", "name": "Stripe Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs", "parser": "greenhouse",
                "company_slug": "stripe", "company_tier": "MNC"
            },
            {
                "id": "gh_figma", "name": "Figma Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/figma/jobs", "parser": "greenhouse",
                "company_slug": "figma", "company_tier": "MNC"
            },
            {
                "id": "gh_gitlab", "name": "GitLab Careers", "type": "ATS", "region": "Worldwide",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/gitlab/jobs", "parser": "greenhouse",
                "company_slug": "gitlab", "company_tier": "MNC"
            },
            {
                "id": "gh_cloudflare", "name": "Cloudflare Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs", "parser": "greenhouse",
                "company_slug": "cloudflare", "company_tier": "MNC"
            },
            {
                "id": "gh_databricks", "name": "Databricks Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/databricks/jobs", "parser": "greenhouse",
                "company_slug": "databricks", "company_tier": "MNC"
            },
            {
                "id": "gh_airbnb", "name": "Airbnb Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/airbnb/jobs", "parser": "greenhouse",
                "company_slug": "airbnb", "company_tier": "MNC"
            },
            {
                "id": "gh_discord", "name": "Discord Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/discord/jobs", "parser": "greenhouse",
                "company_slug": "discord", "company_tier": "MNC"
            },
            {
                "id": "gh_instacart", "name": "Instacart Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/instacart/jobs", "parser": "greenhouse",
                "company_slug": "instacart", "company_tier": "Corporate"
            },
            {
                "id": "gh_reddit", "name": "Reddit Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/reddit/jobs", "parser": "greenhouse",
                "company_slug": "reddit", "company_tier": "Corporate"
            },
            {
                "id": "gh_gusto", "name": "Gusto Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/gusto/jobs", "parser": "greenhouse",
                "company_slug": "gusto", "company_tier": "Corporate"
            },
            {
                "id": "gh_pinterest", "name": "Pinterest Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/pinterest/jobs", "parser": "greenhouse",
                "company_slug": "pinterest", "company_tier": "Corporate"
            },
            {
                "id": "gh_dropbox", "name": "Dropbox Careers", "type": "ATS", "region": "Worldwide",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/dropbox/jobs", "parser": "greenhouse",
                "company_slug": "dropbox", "company_tier": "Corporate"
            },
            {
                "id": "gh_elastic", "name": "Elastic Careers", "type": "ATS", "region": "Worldwide",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/elastic/jobs", "parser": "greenhouse",
                "company_slug": "elastic", "company_tier": "Corporate"
            },
            {
                "id": "gh_cockroach", "name": "Cockroach Labs", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://boards-api.greenhouse.io/v1/boards/cockroachlabs/jobs", "parser": "greenhouse",
                "company_slug": "cockroachlabs", "company_tier": "Corporate"
            },
            # Lever ATS (8)
            {
                "id": "lever_spotify", "name": "Spotify Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/spotify?mode=json", "parser": "lever",
                "company_slug": "spotify", "company_tier": "MNC"
            },
            {
                "id": "lever_palantir", "name": "Palantir Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/palantir?mode=json", "parser": "lever",
                "company_slug": "palantir", "company_tier": "MNC"
            },
            {
                "id": "lever_shopify", "name": "Shopify Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/shopify?mode=json", "parser": "lever",
                "company_slug": "shopify", "company_tier": "MNC"
            },
            {
                "id": "lever_atlassian", "name": "Atlassian Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/atlassian?mode=json", "parser": "lever",
                "company_slug": "atlassian", "company_tier": "MNC"
            },
            {
                "id": "lever_datadog", "name": "Datadog Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/datadog?mode=json", "parser": "lever",
                "company_slug": "datadog", "company_tier": "MNC"
            },
            {
                "id": "lever_kinsta", "name": "Kinsta Careers", "type": "ATS", "region": "Worldwide",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/kinsta?mode=json", "parser": "lever",
                "company_slug": "kinsta", "company_tier": "Corporate"
            },
            {
                "id": "lever_postman", "name": "Postman Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/postman?mode=json", "parser": "lever",
                "company_slug": "postman", "company_tier": "Corporate"
            },
            {
                "id": "lever_docker", "name": "Docker Careers", "type": "ATS", "region": "Worldwide",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.lever.co/v0/postings/docker?mode=json", "parser": "lever",
                "company_slug": "docker", "company_tier": "Corporate"
            },
            # Ashby ATS (8)
            {
                "id": "ashby_openai", "name": "OpenAI Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/openai", "parser": "ashby",
                "company_slug": "openai", "company_tier": "MNC"
            },
            {
                "id": "ashby_notion", "name": "Notion Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/notion", "parser": "ashby",
                "company_slug": "notion", "company_tier": "MNC"
            },
            {
                "id": "ashby_ramp", "name": "Ramp Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/ramp", "parser": "ashby",
                "company_slug": "ramp", "company_tier": "Corporate"
            },
            {
                "id": "ashby_linear", "name": "Linear Careers", "type": "ATS", "region": "Worldwide",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/linear", "parser": "ashby",
                "company_slug": "linear", "company_tier": "Startup"
            },
            {
                "id": "ashby_replit", "name": "Replit Careers", "type": "ATS", "region": "Worldwide",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/replit", "parser": "ashby",
                "company_slug": "replit", "company_tier": "Startup"
            },
            {
                "id": "ashby_perplexity", "name": "Perplexity AI Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/perplexity", "parser": "ashby",
                "company_slug": "perplexity", "company_tier": "Startup"
            },
            {
                "id": "ashby_scale", "name": "Scale AI Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/scaleai", "parser": "ashby",
                "company_slug": "scaleai", "company_tier": "Corporate"
            },
            {
                "id": "ashby_cursor", "name": "Cursor / Anysphere Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.ashbyhq.com/posting-api/job-board/anysphere", "parser": "ashby",
                "company_slug": "anysphere", "company_tier": "Startup"
            },
            # SmartRecruiters ATS (4)
            {
                "id": "sr_visa", "name": "Visa Global Postings", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.smartrecruiters.com/v1/companies/visa/postings", "parser": "smartrecruiters",
                "company_slug": "visa", "company_tier": "MNC"
            },
            {
                "id": "sr_bosch", "name": "Bosch Global Careers", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.smartrecruiters.com/v1/companies/bosch/postings", "parser": "smartrecruiters",
                "company_slug": "bosch", "company_tier": "MNC"
            },
            {
                "id": "sr_skechers", "name": "Skechers Global Postings", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.smartrecruiters.com/v1/companies/skechers/postings", "parser": "smartrecruiters",
                "company_slug": "skechers", "company_tier": "Corporate"
            },
            {
                "id": "sr_equinix", "name": "Equinix Digital Infrastructure", "type": "ATS", "region": "Global",
                "category": "ATS / Career Systems", "enabled": True, "access_method": "ATS_CONNECTOR",
                "endpoint": "https://api.smartrecruiters.com/v1/companies/equinix/postings", "parser": "smartrecruiters",
                "company_slug": "equinix", "company_tier": "Corporate"
            },

            # ==================== 4. COMPANY CAREERS (8) ====================
            {
                "id": "careers_google", "name": "Google Careers Portal", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "DIRECT_CAREER", "endpoint": "https://careers.google.com/jobs/results/",
                "parser": "direct_career", "company_tier": "MNC"
            },
            {
                "id": "careers_microsoft", "name": "Microsoft Careers", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "DIRECT_CAREER", "endpoint": "https://careers.microsoft.com/us/en",
                "parser": "direct_career", "company_tier": "MNC"
            },
            {
                "id": "careers_amazon", "name": "Amazon Jobs", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "DIRECT_CAREER", "endpoint": "https://www.amazon.jobs/en",
                "parser": "direct_career", "company_tier": "MNC"
            },
            {
                "id": "careers_apple", "name": "Apple Jobs", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "DIRECT_CAREER", "endpoint": "https://jobs.apple.com/en-us/search",
                "parser": "direct_career", "company_tier": "MNC"
            },
            {
                "id": "careers_meta", "name": "Meta Careers", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "DIRECT_CAREER", "endpoint": "https://www.metacareers.com/jobs",
                "parser": "direct_career", "company_tier": "MNC"
            },
            {
                "id": "careers_uber", "name": "Uber Careers", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "DIRECT_CAREER", "endpoint": "https://www.uber.com/us/en/careers/",
                "parser": "direct_career", "company_tier": "MNC"
            },
            {
                "id": "careers_nvidia", "name": "NVIDIA Careers (Workday)", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "ATS_CONNECTOR", "endpoint": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
                "parser": "workday", "company_tier": "MNC"
            },
            {
                "id": "careers_salesforce", "name": "Salesforce Careers", "type": "COMPANY_CAREER_PAGE",
                "region": "Global", "category": "Company Careers", "enabled": True,
                "access_method": "ATS_CONNECTOR", "endpoint": "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site",
                "parser": "workday", "company_tier": "MNC"
            },

            # ==================== 5. REGIONAL SOURCES (6) ====================
            {
                "id": "regional_germany_tech", "name": "Germany & DACH Tech Hub", "type": "REGIONAL_JOB_BOARD",
                "region": "Germany", "category": "Regional Sources", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://www.arbeitnow.com/api/job-board-api",
                "parser": "arbeitnow"
            },
            {
                "id": "regional_uk_tech", "name": "United Kingdom Tech Jobs", "type": "REGIONAL_JOB_BOARD",
                "region": "United Kingdom", "category": "Regional Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://uk.indeed.com/jobs",
                "parser": "indeed_global"
            },
            {
                "id": "regional_india_tech", "name": "India Tech Careers", "type": "REGIONAL_JOB_BOARD",
                "region": "India", "category": "Regional Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://in.indeed.com/jobs",
                "parser": "indeed_global"
            },
            {
                "id": "regional_singapore_tech", "name": "Singapore Tech Portals", "type": "REGIONAL_JOB_BOARD",
                "region": "Singapore", "category": "Regional Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://sg.indeed.com/jobs",
                "parser": "indeed_global"
            },
            {
                "id": "regional_canada_tech", "name": "Canada Tech Jobs", "type": "REGIONAL_JOB_BOARD",
                "region": "Canada", "category": "Regional Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://ca.indeed.com/jobs",
                "parser": "indeed_global"
            },
            {
                "id": "regional_australia_tech", "name": "Australia Tech Careers", "type": "REGIONAL_JOB_BOARD",
                "region": "Australia", "category": "Regional Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://au.indeed.com/jobs",
                "parser": "indeed_global"
            },

            # ==================== 6. GOVERNMENT SOURCES (3) ====================
            {
                "id": "gov_usajobs", "name": "USAJOBS Federal Employment", "type": "GOVERNMENT_JOB_PORTAL",
                "region": "United States", "category": "Government Sources", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://data.usajobs.gov/api/jobs",
                "parser": "usajobs"
            },
            {
                "id": "gov_search_gov", "name": "Search.gov US Technology Positions", "type": "GOVERNMENT_JOB_PORTAL",
                "region": "United States", "category": "Government Sources", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://search.usa.gov/jobs/search.json?query=technology",
                "parser": "search_gov"
            },
            {
                "id": "gov_eu_careers", "name": "EU EPSO Public Career Portal", "type": "GOVERNMENT_JOB_PORTAL",
                "region": "European Union", "category": "Government Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://eu-careers.europa.eu",
                "parser": "eu_careers"
            },

            # ==================== 7. BANGLADESH SOURCES (Strictly Isolated) (3) ====================
            {
                "id": "bdjobs_live", "name": "BDJobs Official Job Portal", "type": "REGIONAL_JOB_BOARD",
                "region": "Bangladesh", "category": "Bangladesh Sources", "enabled": True,
                "access_method": "PUBLIC_API", "endpoint": "https://jobs.bdjobs.com",
                "parser": "bdjobs", "notes": "Strictly Bangladesh-only. Excluded from international/worldwide queries."
            },
            {
                "id": "skill_jobs_bd", "name": "Skill.jobs Bangladesh", "type": "REGIONAL_JOB_BOARD",
                "region": "Bangladesh", "category": "Bangladesh Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://skill.jobs",
                "parser": "skill_jobs", "notes": "Local partner portal."
            },
            {
                "id": "chakri_bd", "name": "Chakri.com Bangladesh", "type": "REGIONAL_JOB_BOARD",
                "region": "Bangladesh", "category": "Bangladesh Sources", "enabled": True,
                "access_method": "STRUCTURED_FEED", "endpoint": "https://chakri.com",
                "parser": "chakri", "notes": "Local partner portal."
            }
        ]

        for s in raw_catalog:
            self._sources[s["id"]] = SourceMetadata(**s)

    def _load_state(self):
        """Loads saved health, last_success, and job count state from disk if available."""
        if os.path.exists(self._registry_path):
            try:
                with open(self._registry_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    for sid, data in saved.items():
                        if sid in self._sources:
                            # Update dynamic state fields
                            self._sources[sid].last_success = data.get("last_success")
                            self._sources[sid].last_attempt = data.get("last_attempt")
                            self._sources[sid].last_error = data.get("last_error")
                            self._sources[sid].jobs_found = data.get("jobs_found", 0)
                            self._sources[sid].jobs_deduped = data.get("jobs_deduped", 0)
                            self._sources[sid].status = data.get("status", "UNAVAILABLE")
                            self._sources[sid].http_status = data.get("http_status")
            except Exception:
                pass

    def save_state(self):
        """Persists current health status and metrics to disk."""
        with self._lock:
            try:
                os.makedirs(os.path.dirname(self._registry_path), exist_ok=True)
                data = {sid: s.model_dump() for sid, s in self._sources.items()}
                with open(self._registry_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

    def get_source(self, source_id: str) -> Optional[SourceMetadata]:
        return self._sources.get(source_id)

    def get_all_sources(self) -> List[SourceMetadata]:
        return list(self._sources.values())

    def get_active_sources(self) -> List[SourceMetadata]:
        return [s for s in self._sources.values() if s.status in ["ACTIVE", "PARTIAL"]]

    def get_sources_by_category(self, category: str) -> List[SourceMetadata]:
        return [s for s in self._sources.values() if s.category == category]

    def update_source_status(
        self,
        source_id: str,
        status: str,
        jobs_found: int = 0,
        jobs_deduped: int = 0,
        http_status: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        with self._lock:
            if source_id not in self._sources:
                return
            src = self._sources[source_id]
            now_iso = datetime.now(timezone.utc).isoformat()
            src.last_attempt = now_iso
            src.status = status
            src.http_status = http_status
            
            if status in ["ACTIVE", "PARTIAL"]:
                src.last_success = now_iso
                src.last_error = None
                src.jobs_found = jobs_found
                src.jobs_deduped = jobs_deduped
            else:
                src.last_error = error_message

    def get_health_summary(self) -> Dict[str, Any]:
        """Provides diagnostic health summary for developer/admin dashboard."""
        all_srcs = self.get_all_sources()
        active = [s for s in all_srcs if s.status == "ACTIVE"]
        partial = [s for s in all_srcs if s.status == "PARTIAL"]
        unavail = [s for s in all_srcs if s.status == "UNAVAILABLE"]
        error = [s for s in all_srcs if s.status == "ERROR"]

        by_cat = {}
        for cat in SOURCE_CATEGORIES:
            cat_sources = [s for s in all_srcs if s.category == cat]
            by_cat[cat] = {
                "total": len(cat_sources),
                "active": len([s for s in cat_sources if s.status in ["ACTIVE", "PARTIAL"]]),
                "jobs_found": sum(s.jobs_found for s in cat_sources)
            }

        return {
            "total_registered_sources": len(all_srcs),
            "active_sources_count": len(active),
            "partial_sources_count": len(partial),
            "unavailable_sources_count": len(unavail),
            "error_sources_count": len(error),
            "total_jobs_ingested": sum(s.jobs_found for s in all_srcs),
            "total_jobs_deduped": sum(s.jobs_deduped for s in all_srcs),
            "by_category": by_cat,
            "sources": [s.model_dump() for s in all_srcs]
        }

# Global Singleton
source_registry = SourceRegistry()
