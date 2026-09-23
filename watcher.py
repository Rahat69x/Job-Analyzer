import time
import json
import os
import argparse
from datetime import datetime, timezone
from tabulate import tabulate

from core.models import UserProfile, ScoringWeights
from core.db import init_db, upsert_jobs
from ingestion.bdjobs_client import BDJobsClient
from ingestion.public_portals import fetch_sample_partner_jobs
from scoring.scorer import JobScorer

ALERTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "alerts.json")

def run_watcher(
    categories=[8, 1, 6], 
    skills=["Python", "React", "Audit", "FastAPI"], 
    experience=4.0, 
    threshold=0.80,
    interval_seconds=3600,
    run_once=True
):
    init_db()
    client = BDJobsClient()
    scorer = JobScorer()
    
    profile = UserProfile(
        target_category_ids=categories,
        skills=skills,
        experience_years=experience
    )
    
    print(f"=== bd-job-analyzer Automated Watcher ===")
    print(f"Monitoring Categories: {categories}")
    print(f"Threshold: Score >= {threshold}")
    print(f"Profile: Exp {experience}y | Skills: {skills}\n")

    while True:
        all_new_alerts = []
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        print(f"[{now_str}] Polling live job portals...")

        for cat_id in categories:
            cat_info = client.get_category_info(cat_id)
            jobs = client.fetch_jobs_by_category(cat_id, page=1, rpp=50)
            partner_jobs = fetch_sample_partner_jobs(cat_id, cat_info['name'])
            jobs.extend(partner_jobs)

            # Persist to SQLite
            upsert_jobs(jobs)

            # Rank
            ranked = scorer.rank_jobs(jobs, profile)
            high_scorers = [item for item in ranked if item.score.final_score >= threshold]

            for item in high_scorers:
                all_new_alerts.append({
                    "timestamp": now_str,
                    "job_id": item.job.id,
                    "title": item.job.title,
                    "company": item.job.company.name,
                    "category": item.job.category_name,
                    "score": item.score.final_score,
                    "explanation": item.score.explanation,
                    "salary": item.job.salary.raw_text,
                    "apply_url": item.job.apply_url
                })

        # Save to alerts.json
        existing_alerts = []
        if os.path.exists(ALERTS_PATH):
            try:
                with open(ALERTS_PATH, "r", encoding="utf-8") as f:
                    existing_alerts = json.load(f)
            except Exception:
                pass
                
        # Merge by job_id
        seen_ids = {a['job_id'] for a in existing_alerts}
        new_count = 0
        for alert in all_new_alerts:
            if alert['job_id'] not in seen_ids:
                existing_alerts.append(alert)
                seen_ids.add(alert['job_id'])
                new_count += 1

        with open(ALERTS_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_alerts, f, indent=2, ensure_ascii=False)

        print(f" -> Found {len(all_new_alerts)} high-match jobs ({new_count} newly alerted).")

        if all_new_alerts:
            table_data = [
                [a['title'][:32], a['company'][:20], a['category'][:18], a['salary'][:20], f"{a['score']:.3f}", a['apply_url']]
                for a in all_new_alerts[:10]
            ]
            print(tabulate(table_data, headers=["Title", "Company", "Category", "Salary", "Score", "Apply Link"], tablefmt="github"))

        if run_once:
            print("\nWatcher single pass complete. Alerts saved to data/alerts.json.")
            break

        print(f"Sleeping for {interval_seconds} seconds...\n")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="bd-job-analyzer automated watcher")
    parser.add_argument("--categories", nargs="+", type=int, default=[8, 1], help="Category IDs to monitor (default: 8 1)")
    parser.add_argument("--skills", type=str, default="Python, React, Audit", help="Comma-separated skills")
    parser.add_argument("--experience", type=float, default=4.0, help="Years of experience")
    parser.add_argument("--threshold", type=float, default=0.80, help="Minimum score threshold (default: 0.80)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background")
    parser.add_argument("--interval", type=int, default=3600, help="Polling interval in seconds")

    args = parser.parse_args()
    skills_list = [s.strip() for s in args.skills.split(",") if s.strip()]

    run_watcher(
        categories=args.categories,
        skills=skills_list,
        experience=args.experience,
        threshold=args.threshold,
        interval_seconds=args.interval,
        run_once=not args.daemon
    )
