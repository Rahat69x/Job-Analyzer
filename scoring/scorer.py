import math
from datetime import datetime, timezone
from typing import List, Dict, Optional
from core.models import NormalizedJob, UserProfile, ScoringWeights, ScoreBreakdown, ScoredJob

# Category salary benchmarks in BDT for typical mid-level openings
CATEGORY_SALARY_BENCHMARKS = {
    8: 75000,    # IT/Telecommunication
    1: 55000,    # Accounting/Finance
    2: 65000,    # Bank/Non-Bank Fin. Inst.
    5: 60000,    # Engineer/Architect
    6: 55000,    # Garments/Textile
    9: 45000,    # Marketing/Sales
    3: 55000,    # Supply Chain/Procurement
    17: 50000,   # HR/Org. Development
    18: 50000,   # Design/Creative
    30: 50000,   # E-commerce/Digital Marketing
    12: 60000,   # NGO/Development
    29: 50000,   # Pharmaceutical
    22: 45000,   # Law/Legal
}
DEFAULT_BENCHMARK = 50000

EMPLOYER_TIER_SCORES = {
    "MNC": 1.00,
    "Financial Institution": 0.95,
    "Conglomerate": 0.90,
    "Corporate": 0.80,
    "Startup": 0.70,
    "SME": 0.60,
    "Confidential": 0.25
}

class JobScorer:
    def __init__(self, weights: Optional[ScoringWeights] = None):
        self.weights = weights or ScoringWeights()

    def calculate_recency_score(self, pub_date: Optional[datetime], deadline: Optional[datetime]) -> float:
        now = datetime.now(timezone.utc)
        
        # Check deadline
        if deadline and deadline < now:
            return 0.05
            
        if not pub_date:
            return 0.50
            
        delta_days = max(0.0, (now - pub_date).total_seconds() / 86400.0)
        # Exponential decay with 7-day half life
        score = math.exp(-delta_days / 7.0)
        return max(0.05, min(1.0, score))

    def calculate_salary_score(self, job: NormalizedJob) -> float:
        if not job.salary.disclosed or not job.salary.min_salary:
            return 0.35  # Opacity penalty for "Negotiable"
            
        midpoint = (job.salary.min_salary + (job.salary.max_salary or job.salary.min_salary)) / 2.0
        benchmark = CATEGORY_SALARY_BENCHMARKS.get(job.category_id, DEFAULT_BENCHMARK)
        
        ratio = midpoint / float(benchmark)
        # Base reward for disclosure is 0.70, up to 1.00 for competitive packages
        score = 0.70 + 0.30 * min(1.0, ratio)
        return max(0.40, min(1.0, score))

    def calculate_profile_match(self, job: NormalizedJob, profile: UserProfile) -> float:
        # 1. Category fit
        cat_fit = 1.0
        if profile.target_category_ids:
            cat_fit = 1.0 if job.category_id in profile.target_category_ids else 0.40
            
        # 2. Skill keywords match
        skill_score = 0.50
        if profile.skills:
            searchable_text = f"{job.title} {job.job_context}".lower()
            matched_count = 0
            for skill in profile.skills:
                skill_clean = skill.strip().lower()
                if skill_clean and skill_clean in searchable_text:
                    matched_count += 1
            skill_score = matched_count / max(1, len(profile.skills))
            
        # 3. Experience fit
        exp_score = 1.0
        req_min = job.experience.min_years or 0.0
        req_max = job.experience.max_years or 99.0
        user_exp = profile.experience_years
        
        if req_min <= user_exp <= req_max:
            exp_score = 1.0
        elif user_exp > req_max:
            exp_score = 0.85  # Mild overqualification
        else:
            diff = req_min - user_exp
            if diff <= 1.0:
                exp_score = 0.70
            elif diff <= 2.0:
                exp_score = 0.45
            else:
                exp_score = 0.20
                
        # 4. Candidate geographic and remote eligibility
        eligibility_factor = 1.0
        if hasattr(job, 'candidate_eligibility') and job.candidate_eligibility:
            if job.candidate_eligibility.status == "ineligible":
                eligibility_factor = 0.35  # Heavy demotion for positions candidate cannot legally/geographically hold
            elif job.candidate_eligibility.status == "conditional":
                eligibility_factor = 0.70

        # 5. Preferred country bonus
        country_bonus = 0.0
        if profile.preferred_countries:
            if any(c.lower() == job.country.lower() for c in profile.preferred_countries):
                country_bonus = 0.15

        # 6. Remote preference bonus
        remote_bonus = 0.0
        if "Remote" in profile.preferred_workplace_type and job.workplace_type == "Remote":
            remote_bonus = 0.10

        # Composite profile score
        base_match = (0.40 * skill_score) + (0.35 * exp_score) + (0.15 * cat_fit) + country_bonus + remote_bonus
        return min(1.0, max(0.10, base_match * eligibility_factor))

    def calculate_employer_score(self, job: NormalizedJob) -> float:
        tier_score = EMPLOYER_TIER_SCORES.get(job.company.tier, 0.60)
        if job.company.verified:
            tier_score = min(1.0, tier_score + 0.05)
        return tier_score

    def score_job(self, job: NormalizedJob, profile: UserProfile) -> ScoredJob:
        s_rec = self.calculate_recency_score(job.publish_date, job.deadline)
        s_sal = self.calculate_salary_score(job)
        s_prof = self.calculate_profile_match(job, profile)
        s_emp = self.calculate_employer_score(job)
        
        final = (
            (self.weights.w_recency * s_rec) +
            (self.weights.w_salary * s_sal) +
            (self.weights.w_profile * s_prof) +
            (self.weights.w_employer * s_emp)
        )
        final = round(final, 3)
        
        explanations = []
        if s_rec > 0.80:
            explanations.append("Freshly posted")
        if job.salary.disclosed:
            explanations.append(f"Transparent salary ({job.salary.raw_text})")
        else:
            explanations.append("Salary negotiable")
        if s_prof > 0.75:
            explanations.append("Strong profile & skill match")
        if s_emp >= 0.85:
            explanations.append(f"Top tier employer ({job.company.tier})")
            
        breakdown = ScoreBreakdown(
            recency_score=round(s_rec, 2),
            salary_score=round(s_sal, 2),
            profile_match_score=round(s_prof, 2),
            employer_score=round(s_emp, 2),
            final_score=final,
            explanation="; ".join(explanations)
        )
        
        return ScoredJob(job=job, score=breakdown)

    def rank_jobs(self, jobs: List[NormalizedJob], profile: UserProfile) -> List[ScoredJob]:
        scored = [self.score_job(j, profile) for j in jobs]
        scored.sort(key=lambda x: x.score.final_score, reverse=True)
        return scored
