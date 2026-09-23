import re
import hashlib
from typing import List, Dict
from core.models import NormalizedJob

def clean_for_dedup(text: str) -> str:
    """Normalize text for hash comparison."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[\(\)\[\],.\-_/:]', ' ', text)
    # Remove common filler words & legal entity indicators
    text = re.sub(r'\b(senior|junior|lead|principal|staff|intern|the|ltd|limited|llc|inc|corp|corporation|gmbh|co|pvt|technologies|solutions|group)\b', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def compute_canonical_id(job: NormalizedJob) -> str:
    """Generate a reproducible canonical hash for cross-portal deduplication."""
    norm_comp = clean_for_dedup(job.company.name)
    norm_title = clean_for_dedup(job.title)
    norm_loc = clean_for_dedup(job.country)
    
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
