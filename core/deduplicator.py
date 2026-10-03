"""
Intelligent Cross-Platform Job Deduplication
Deduplicates postings appearing across multiple boards and ATS platforms
while preserving complete source provenance and richest metadata.
"""

import re
import hashlib
from typing import List, Dict
from core.models import NormalizedJob

def clean_company_name(text: str) -> str:
    """Normalize company name by stripping legal entities and filler."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r'[\(\)\[\],.\-_/:]', ' ', t)
    t = re.sub(r'\b(the|ltd|limited|llc|inc|corp|corporation|gmbh|co|pvt|technologies|solutions|group|holdings)\b', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def clean_title(text: str) -> str:
    """Normalize job title preserving seniority level, sorted for order invariance."""
    if not text:
        return ""
    t = text.lower()
    t = re.sub(r'[\(\)\[\],.\-_/:]', ' ', t)
    tokens = [w for w in t.split() if w]
    tokens.sort()
    return " ".join(tokens)

def compute_canonical_id(job: NormalizedJob) -> str:
    """Generate a reproducible canonical hash for cross-portal deduplication."""
    norm_comp = clean_company_name(job.company.name if job.company else "")
    norm_title = clean_title(job.title)
    norm_loc = clean_company_name(job.country or job.location)
    
    key = f"{norm_comp}::{norm_title}::{norm_loc}"
    return hashlib.md5(key.encode("utf-8")).hexdigest()[:16]

def deduplicate_jobs(jobs: List[NormalizedJob]) -> List[NormalizedJob]:
    """
    Deduplicate cross-platform job listings.
    Prioritizes official company career pages or verified sources,
    and aggregates all appearing portals into alternate_sources.
    """
    seen: Dict[str, NormalizedJob] = {}
    
    # Priority rank: higher is better
    reliability_ranks = {
        "official_career_page": 5,
        "verified_partner": 4,
        "major_board": 3,
        "third_party": 2,
        "agency": 1
    }
    
    for job in jobs:
        canon_id = job.canonical_id or compute_canonical_id(job)
        job.canonical_id = canon_id
        
        if canon_id not in seen:
            seen[canon_id] = job
        else:
            existing = seen[canon_id]
            # Record alternate source
            if job.source not in existing.alternate_sources and job.source != existing.source:
                existing.alternate_sources.append(job.source)
                
            # If current job has higher source reliability, promote it as primary
            current_rank = reliability_ranks.get(job.source_reliability, 3)
            existing_rank = reliability_ranks.get(existing.source_reliability, 3)
            
            if current_rank > existing_rank:
                job.alternate_sources = list(set([existing.source] + existing.alternate_sources))
                seen[canon_id] = job
                
    return list(seen.values())
