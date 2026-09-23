import argparse
import json
import os
import sys
from tabulate import tabulate
from core.models import UserProfile, ScoringWeights
from ingestion.bdjobs_client import BDJobsClient
from ingestion.public_portals import fetch_sample_partner_jobs
from ingestion.linkedin_parser import parse_pasted_linkedin_text
from scoring.scorer import JobScorer

def main():
    parser = argparse.ArgumentParser(description="bd-job-analyzer: Surface & rank the best jobs in Bangladesh.")
    parser.add_argument("--category", "-c", type=int, default=8, help="Category ID (e.g., 8 for IT/Telecommunication, 1 for Accounting/Finance)")
    parser.add_argument("--skills", "-s", type=str, default="", help="Comma-separated skills (e.g. 'Python, React, AWS')")
    parser.add_argument("--experience", "-e", type=float, default=3.0, help="Years of experience (default: 3.0)")
    parser.add_argument("--limit", "-l", type=int, default=15, help="Number of jobs to display (default: 15)")
    parser.add_argument("--list-categories", action="store_true", help="List all 64 verified BDJobs categories with active vacancy stats")
    parser.add_argument("--include-partners", action="store_true", default=True, help="Include partner portals (Skill.jobs, Chakri)")
    parser.add_argument("--paste-linkedin", type=str, default="", help="Path to text file containing pasted LinkedIn job post")

    args = parser.parse_args()

    client = BDJobsClient()

    if args.list_categories:
        taxonomy = client.taxonomy.get('categories', [])
        table_data = []
        for cat in taxonomy:
            table_data.append([
                cat['id'],
                cat['name'],
                cat['type'],
                f"{cat.get('active_jobs', 0):,}",
                f"{cat.get('total_vacancies', 0):,}",
                f"{cat.get('total_cvs', 0):,}"
            ])
        print("\n=== BDJobs Verified 64-Category Taxonomy Map ===")
        print(tabulate(table_data, headers=["ID", "Category Name", "Type", "Active Jobs", "Vacancies", "Registered CVs"], tablefmt="github"))
        return

    skills_list = [s.strip() for s in args.skills.split(",") if s.strip()]
    profile = UserProfile(
        target_category_ids=[args.category],
        skills=skills_list,
        experience_years=args.experience
    )

    cat_info = client.get_category_info(args.category)
    print(f"\n[bd-job-analyzer] Querying live openings for: {cat_info['name']} (ID: {args.category})")
    print(f"[Profile] Experience: {args.experience} years | Skills: {skills_list or 'Any'}")
    
    # Ingest BDJobs
    jobs = client.fetch_jobs_by_category(args.category, page=1, rpp=50)
    print(f" -> Ingested {len(jobs)} live listings from BDJobs.com REST API.")

    # Ingest Partner Portals
    if args.include_partners:
        partner_jobs = fetch_sample_partner_jobs(args.category, cat_info['name'])
        if partner_jobs:
            jobs.extend(partner_jobs)
            print(f" -> Aggregated {len(partner_jobs)} cross-portal openings from Skill.jobs & Chakri.com.")

    # Ingest LinkedIn Paste if supplied
    if args.paste_linkedin and os.path.exists(args.paste_linkedin):
        with open(args.paste_linkedin, 'r', encoding='utf-8') as f:
            li_text = f.read()
        li_job = parse_pasted_linkedin_text(li_text, args.category, cat_info['name'])
        if li_job:
            jobs.append(li_job)
            print(f" -> Ingested 1 verified job from pasted LinkedIn text.")

    if not jobs:
        print("No jobs found matching criteria.")
        return

    # Score and Rank
    scorer = JobScorer()
    ranked_jobs = scorer.rank_jobs(jobs, profile)

    # Output Table: Job Title | Company | Category | Posted date | Salary (if shown) | Score | Apply link
    table_rows = []
    for idx, item in enumerate(ranked_jobs[:args.limit], 1):
        j = item.job
        s = item.score
        
        pub_str = j.publish_date.strftime("%Y-%m-%d") if j.publish_date else "Recent"
        salary_str = j.salary.raw_text if j.salary.disclosed else "Negotiable"
        
        # Format score with explanation
        score_display = f"{s.final_score:.3f}"
        
        table_rows.append([
            idx,
            j.title[:35],
            f"{j.company.name[:22]} [{j.source}]",
            j.category_name[:18],
            pub_str,
            salary_str[:22],
            score_display,
            j.apply_url
        ])

    headers = ["#", "Job Title", "Company", "Category", "Posted Date", "Salary", "Score", "Apply Link"]
    print(f"\n=== Top Ranked Openings in Bangladesh ({cat_info['name']}) ===")
    print(tabulate(table_rows, headers=headers, tablefmt="github"))
    print(f"\nShowing top {min(args.limit, len(ranked_jobs))} of {len(ranked_jobs)} evaluated listings.")

if __name__ == "__main__":
    main()
