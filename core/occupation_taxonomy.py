"""
Controlled Synonym & Occupation Taxonomy
Provides deliberate, curated semantic expansions for tech, engineering, and data professions.
Expands queries into high-precision equivalents without unbounded noise.
"""

from typing import List, Dict, Set
import re

OCCUPATION_SYNONYMS: Dict[str, List[str]] = {
    "cybersecurity analyst": [
        "cybersecurity analyst",
        "cyber security analyst",
        "information security analyst",
        "security analyst",
        "soc analyst",
        "cyber defense analyst",
        "security operations analyst",
        "infosec analyst",
        "security engineer",
        "threat intelligence analyst"
    ],
    "c++ developer": [
        "c++ developer",
        "c++ software engineer",
        "c++ engineer",
        "c++ backend engineer",
        "c++ systems engineer",
        "embedded c++",
        "c/c++ developer",
        "c/c++ software engineer",
        "systems engineer c++"
    ],
    "java developer": [
        "java developer",
        "java software engineer",
        "java backend engineer",
        "java engineer",
        "senior java developer",
        "core java developer",
        "spring boot developer",
        "java/spring developer"
    ],
    "software engineer": [
        "software engineer",
        "software developer",
        "full stack engineer",
        "full stack developer",
        "backend engineer",
        "frontend engineer",
        "systems software engineer",
        "swe"
    ],
    "machine learning engineer": [
        "machine learning engineer",
        "ml engineer",
        "machine learning scientist",
        "ai/ml engineer",
        "deep learning engineer",
        "applied machine learning engineer",
        "mle"
    ],
    "data analyst": [
        "data analyst",
        "business intelligence analyst",
        "bi analyst",
        "analytics engineer",
        "product analyst",
        "data visualization analyst",
        "quantitative analyst"
    ],
    "frontend developer": [
        "frontend developer",
        "front end developer",
        "frontend engineer",
        "front end engineer",
        "ui engineer",
        "react developer",
        "react engineer",
        "web developer"
    ],
    "backend developer": [
        "backend developer",
        "back end developer",
        "backend engineer",
        "back end engineer",
        "api engineer",
        "server engineer",
        "cloud backend engineer"
    ],
    "ai engineer": [
        "ai engineer",
        "artificial intelligence engineer",
        "generative ai engineer",
        "ai research engineer",
        "llm engineer",
        "ai application engineer"
    ],
    "internship": [
        "internship",
        "software engineer intern",
        "engineering intern",
        "summer intern",
        "graduate intern",
        "trainee",
        "co-op",
        "intern "
    ],
    "data engineer": [
        "data engineer",
        "big data engineer",
        "data platform engineer",
        "etl developer",
        "pipeline engineer",
        "analytics engineer"
    ],
    "devops engineer": [
        "devops engineer",
        "site reliability engineer",
        "sre",
        "cloud infrastructure engineer",
        "platform engineer",
        "cloud engineer",
        "infrastructure engineer"
    ],
    "product manager": [
        "product manager",
        "technical product manager",
        "associate product manager",
        "group product manager",
        "pm"
    ],
    "qa engineer": [
        "qa engineer",
        "quality assurance engineer",
        "sdet",
        "software test engineer",
        "automation test engineer",
        "test automation engineer"
    ]
}

def normalize_search_query(query: str) -> List[str]:
    """
    Expands query using deliberate occupation taxonomy when a match is found.
    If no specific taxonomy matches, returns the original normalized query token.
    """
    if not query:
        return []
    
    clean_q = re.sub(r"[^\w\s\+\#/-]", " ", query).strip().lower()
    clean_q = re.sub(r"\s+", " ", clean_q)
    
    # Direct match in taxonomy
    for key, synonyms in OCCUPATION_SYNONYMS.items():
        if key in clean_q or clean_q in key:
            # Found exact or substring occupation match
            return synonyms

    # Partial / phrase match check
    for key, synonyms in OCCUPATION_SYNONYMS.items():
        tokens = key.split()
        if all(token in clean_q for token in tokens):
            return synonyms
            
    # Default: return the clean query itself as a single term
    return [clean_q]
